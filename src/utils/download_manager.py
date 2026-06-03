import threading
import time
from pathlib import Path


class DownloadManager:
    """Manages downloads with progress tracking and thread-safe state."""

    def __init__(self, jellyfin=None):
        self.jellyfin = jellyfin
        self._lock = threading.Lock()
        self.current_download_id = None
        self.current_progress = 0  # 0-100
        self.current_status = "idle"  # idle/downloading/failed
        self.error_message = None
        self.is_album_download = False  # True if downloading full album

        # Start worker thread
        self._should_stop = False
        self._worker_thread = threading.Thread(target=self._download_worker, daemon=True)
        self._worker_thread.start()

    def start_download(self, item_id, is_album=False):
        """Start downloading a song or album. Returns True if started successfully."""
        with self._lock:
            if self.current_download_id:
                return False  # Already downloading

            self.current_download_id = item_id
            self.current_progress = 0
            self.current_status = "downloading"
            self.error_message = None
            self.is_album_download = is_album
            return True

    def update_progress(self, percent):
        """Update download progress (0-100)."""
        with self._lock:
            if percent <= 100:
                self.current_progress = percent

    def complete_download(self):
        """Mark current download as complete."""
        with self._lock:
            self.current_download_id = None
            self.current_progress = 0
            self.current_status = "idle"
            self.error_message = None
            self.is_album_download = False

    def fail_download(self, error_message):
        """Mark current download as failed."""
        with self._lock:
            self.current_status = "failed"
            self.error_message = error_message

    def retry_download(self):
        """Retry a failed download."""
        with self._lock:
            if self.current_status == "failed" and self.current_download_id:
                self.current_progress = 0
                self.current_status = "downloading"
                self.error_message = None
                return True
            return False

    def get_state(self):
        """Get current download state (thread-safe copy)."""
        with self._lock:
            return {
                "current_download_id": self.current_download_id,
                "current_progress": self.current_progress,
                "current_status": self.current_status,
                "error_message": self.error_message,
                "is_album_download": self.is_album_download,
            }

    def is_downloading(self):
        """Check if a download is in progress."""
        with self._lock:
            return self.current_download_id is not None

    def cancel_download(self):
        """Cancel current download."""
        with self._lock:
            self.current_download_id = None
            self.current_progress = 0
            self.current_status = "idle"
            self.error_message = None
            self.is_album_download = False

    def _download_worker(self):
        """Background worker thread for downloads."""
        while not self._should_stop:
            state = self.get_state()

            if state["current_download_id"]:
                if not self.jellyfin:
                    self.fail_download("Jellyfin client not available")
                else:
                    try:
                        if state["is_album_download"]:
                            self._download_album(state["current_download_id"])
                        else:
                            self._download_song(state["current_download_id"])
                        self.complete_download()
                    except Exception as e:
                        self.fail_download(str(e))

            time.sleep(0.1)

    def _download_song(self, song_id):
        """Download a single song with progress tracking."""
        # Use streaming download to track progress
        response = self.jellyfin.session.get(
            self.jellyfin._build_url(f"Items/{song_id}/Download?Static=true"),
            stream=True,
            timeout=60
        )

        if response.status_code >= 400:
            from src.utils.jellyfin import JellyfinError
            raise JellyfinError(f"Download failed ({response.status_code})")

        # Get item details for path construction
        item = self.jellyfin.get_item(song_id, fields=["Album", "AlbumId", "Artists", "AlbumArtists", "Path", "MediaSources"])
        album = self.jellyfin._sanitize_path_component(item.get("Album") or "Unknown Album")
        artists = item.get("Artists") or item.get("AlbumArtists") or ["Unknown Artist"]
        artist = self.jellyfin._sanitize_path_component(artists[0])

        album_folder = self.jellyfin._ensure_download_root() / artist / album
        album_folder.mkdir(parents=True, exist_ok=True)

        # Get filename
        media_sources = item.get("MediaSources") or []
        if media_sources and isinstance(media_sources, list):
            container = media_sources[0].get("Container")
            if container:
                filename = f"{self.jellyfin._sanitize_path_component(item.get('Name') or song_id)}.{container.lower()}"
            else:
                filename = f"{self.jellyfin._sanitize_path_component(item.get('Name') or song_id)}.mp3"
        else:
            filename = f"{self.jellyfin._sanitize_path_component(item.get('Name') or song_id)}.mp3"

        target_path = album_folder / filename

        # Download with progress tracking
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        self.update_progress(progress)

        # Download album art if not already present
        album_id = item.get("AlbumId")
        if album_id:
            self.jellyfin._download_album_art(album_id, album_folder)

    def _download_album(self, album_id):
        """Download all songs in an album."""
        songs = self.jellyfin.get_songs(album_id=album_id)

        for idx, song in enumerate(songs):
            self._download_song(song["Id"])
            # Update overall progress for album
            progress = int((idx / len(songs)) * 100)
            self.update_progress(progress)

        # Ensure we hit 100%
        self.update_progress(100)

    def cleanup(self):
        """Clean up resources."""
        self._should_stop = True

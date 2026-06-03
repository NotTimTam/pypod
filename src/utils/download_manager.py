import threading
import time
from pathlib import Path

from src.utils.jellyfin import JellyfinError


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
        self.current_download_total = 0  # For album progress tracking

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
            self.current_download_total = 0
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
            self.current_download_total = 0

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
            self.current_download_total = 0

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
        # Get item metadata
        item = self.jellyfin.get_item(
            song_id,
            fields=["Album", "AlbumId", "Artists", "AlbumArtists", "MediaSources"]
        )

        # Construct folder path
        album = self.jellyfin._sanitize_path_component(item.get("Album") or "Unknown Album")
        artists = item.get("Artists") or item.get("AlbumArtists") or ["Unknown Artist"]
        artist = self.jellyfin._sanitize_path_component(artists[0])

        download_root = self.jellyfin._ensure_download_root()
        album_folder = download_root / artist / album
        album_folder.mkdir(parents=True, exist_ok=True)

        # Determine filename from MediaSources
        filename = self._get_filename(item, song_id)
        target_path = album_folder / filename

        # Stream download with progress tracking
        response = self.jellyfin.get_item_stream(song_id)
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

        # Download album art if available
        album_id = item.get("AlbumId")
        if album_id:
            art_path = self.jellyfin._album_art_path(album_folder)
            if not art_path.exists():
                self.jellyfin.download_album_art(album_id, art_path)

    def _download_album(self, album_id):
        """Download all songs in an album with progress tracking."""
        songs = self.jellyfin.get_songs(album_id=album_id)
        
        with self._lock:
            self.current_download_total = len(songs)

        for idx, song in enumerate(songs):
            # Download individual song
            self._download_song(song["Id"])
            
            # Update album-level progress (idx+1 because idx starts at 0)
            album_progress = int(((idx + 1) / len(songs)) * 100)
            self.update_progress(album_progress)

    @staticmethod
    def _get_filename(item, item_id):
        """Extract filename from item metadata."""
        media_sources = item.get("MediaSources") or []
        
        if media_sources and isinstance(media_sources, list):
            container = media_sources[0].get("Container")
            if container:
                return f"{item.get('Name') or item_id}.{container.lower()}"
        
        return f"{item.get('Name') or item_id}.mp3"

    def cleanup(self):
        """Clean up resources."""
        self._should_stop = True
        self._worker_thread.join(timeout=5)
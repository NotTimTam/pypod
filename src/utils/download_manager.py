import threading
import time
from collections import deque


class DownloadManager:
    """Manages downloads with progress tracking, queue, and gentle resource usage for Pi Zero."""

    def __init__(self, jellyfin=None):
        self.jellyfin = jellyfin
        self._lock = threading.Lock()
        self.current_download_id = None
        self.current_progress = 0  # 0-100
        self.current_status = "idle"  # idle/downloading/failed
        self.error_message = None
        self.is_album_download = False

        # Download queue for gentle processing
        self._download_queue = deque()
        self._queue_lock = threading.Lock()

        # Rate limiting - delay between downloads
        self._last_download_time = 0
        self.download_delay_seconds = 2  # Gentle delay between downloads

        # Memory-efficient streaming
        self.chunk_size = 4096  # Smaller chunks for Pi Zero
        self.bandwidth_limit_kbps = (
            None  # Optional bandwidth throttling (None = unlimited)
        )

        # Album download tracking
        self.album_total_songs = 0
        self.album_current_song = 0

        # Start worker thread
        self._should_stop = False
        self._worker_thread = threading.Thread(
            target=self._download_worker, daemon=True
        )
        self._worker_thread.start()

    def start_download(self, item_id, is_album=False):
        """Queue a download. Returns True if queued successfully."""
        with self._queue_lock:
            # Check if already queued or downloading
            if self.current_download_id == item_id:
                return False

            for queued_id, _ in self._download_queue:
                if queued_id == item_id:
                    return False  # Already in queue

            self._download_queue.append((item_id, is_album))
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
            self.album_total_songs = 0
            self.album_current_song = 0

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
                "album_total_songs": self.album_total_songs,
                "album_current_song": self.album_current_song,
                "queue_size": len(self._download_queue),
            }

    def is_downloading(self):
        """Check if a download is in progress."""
        with self._lock:
            return self.current_download_id is not None

    def has_queued_downloads(self):
        """Check if there are queued downloads waiting."""
        with self._queue_lock:
            return len(self._download_queue) > 0

    def cancel_download(self):
        """Cancel current download and queue."""
        with self._lock:
            self.current_download_id = None
            self.current_progress = 0
            self.current_status = "idle"
            self.error_message = None
            self.is_album_download = False

        with self._queue_lock:
            self._download_queue.clear()

    def _get_next_queued_download(self):
        """Get next download from queue (thread-safe)."""
        with self._queue_lock:
            if self._download_queue:
                return self._download_queue.popleft()
        return None

    def _download_worker(self):
        """Background worker thread for downloads - processes one at a time."""
        while not self._should_stop:
            # Check if we should process next queued download
            if not self.is_downloading():
                next_download = self._get_next_queued_download()
                if next_download:
                    item_id, is_album = next_download

                    # Gentle delay between downloads
                    time_since_last = time.time() - self._last_download_time
                    if time_since_last < self.download_delay_seconds:
                        time.sleep(self.download_delay_seconds - time_since_last)

                    self._last_download_time = time.time()

                    with self._lock:
                        self.current_download_id = item_id
                        self.current_progress = 0
                        self.current_status = "downloading"
                        self.error_message = None
                        self.is_album_download = is_album

                    # Perform the download
                    try:
                        if is_album:
                            self._download_album(item_id)
                        else:
                            self._download_song(item_id)
                        self.complete_download()
                    except Exception as e:
                        print(f"Download error: {e}")
                        self.fail_download(str(e))

            time.sleep(0.2)

    def _download_song(self, song_id):
        """Download a single song with progress tracking and bandwidth control."""
        # Get item details for path construction
        item = self.jellyfin.get_item(
            song_id,
            fields=[
                "Album",
                "AlbumId",
                "Artists",
                "AlbumArtists",
                "Path",
                "MediaSources",
            ],
        )
        album = self.jellyfin._sanitize_path_component(
            item.get("Album") or "Unknown Album"
        )
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

        # Skip if already exists
        if target_path.exists():
            self.update_progress(100)
            return

        # Use streaming download to track progress with bandwidth control
        response = self.jellyfin.session.get(
            self.jellyfin._build_url(f"Items/{song_id}/Download?Static=true"),
            stream=True,
            timeout=60,
        )

        if response.status_code >= 400:
            from src.utils.jellyfin import JellyfinError

            raise JellyfinError(f"Download failed ({response.status_code})")

        # Download with progress tracking and bandwidth throttling
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        chunk_start_time = time.time()

        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Update progress
                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        self.update_progress(progress)

                    # Bandwidth throttling
                    if self.bandwidth_limit_kbps:
                        elapsed = time.time() - chunk_start_time
                        expected_time = (len(chunk) / 1024) / self.bandwidth_limit_kbps
                        if elapsed < expected_time:
                            time.sleep(expected_time - elapsed)
                        chunk_start_time = time.time()

        # Download album art if not already present (small file, less critical)
        try:
            album_id = item.get("AlbumId")
            if album_id:
                self.jellyfin._download_album_art(album_id, album_folder)
        except Exception as e:
            # Art download failure shouldn't fail the whole download
            print(f"Warning: Could not download album art: {e}")

    def _download_album(self, album_id):
        """Download all songs in an album sequentially."""
        songs = self.jellyfin.get_songs(album_id=album_id)

        if not songs:
            raise Exception("No songs found in album")

        self.album_total_songs = len(songs)

        for idx, song in enumerate(songs):
            self.album_current_song = idx + 1
            self._download_song(song["Id"])

            # Update overall progress for album
            # Weight by song index, accounting for current song's internal progress
            song_progress = int(((idx) / len(songs)) * 100)
            self.update_progress(song_progress)

            # Gentle delay between songs in album (smaller than inter-download delay)
            if idx < len(songs) - 1:
                time.sleep(1)

        # Ensure we hit 100%
        self.update_progress(100)

    def cleanup(self):
        """Clean up resources."""
        self._should_stop = True
        self._worker_thread.join(timeout=2)

import threading
import time
from pathlib import Path

from src.utils.jellyfin import JellyfinError


class DownloadManager:
    """Robust download manager with UI feedback."""

    def __init__(self, jellyfin=None):
        self.jellyfin = jellyfin
        self._lock = threading.Lock()
        self.current_download_id = None
        self.current_progress = 0
        self.current_status = "idle"
        self.error_message = None
        self.is_album_download = False
        self._should_stop = False
        self._worker_thread = threading.Thread(target=self._download_worker, daemon=True)
        self._worker_thread.start()

    # ... (start_download, update_progress, etc. remain mostly same)

    def _download_song(self, song_id):
        """Improved song download with progress."""
        try:
            item = self.jellyfin.get_item(song_id, fields=["Album", "Artists", "Path", "MediaSources"])
            # Use proper download stream
            download_url = f"Items/{song_id}/Download?Static=true"
            response = self.jellyfin.session.get(
                self.jellyfin._build_url(download_url), stream=True, timeout=60
            )
            if response.status_code >= 400:
                raise JellyfinError(f"Download failed: {response.status_code}")

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            artist = self.jellyfin._sanitize_path_component(item.get("Artists", ["Unknown"])[0])
            album = self.jellyfin._sanitize_path_component(item.get("Album", "Unknown"))

            dest_dir = self.jellyfin.download_root / artist / album
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / f"{song_id}_{item.get('Name', 'song')}.mp3"

            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.update_progress(progress)
            # Download art
            self.jellyfin._download_album_art(item.get("AlbumId"), dest_dir)
            return dest_path
        except Exception as e:
            raise

    # Similar improvements for album

    def _download_worker(self):
        while not self._should_stop:
            with self._lock:
                if self.current_download_id and self.current_status == "downloading":
                    try:
                        if self.is_album_download:
                            self._download_album(self.current_download_id)
                        else:
                            self._download_song(self.current_download_id)
                        self.complete_download()
                    except Exception as e:
                        self.fail_download(str(e))
            time.sleep(0.2)

    def cleanup(self):
        self._should_stop = True
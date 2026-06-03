class MenuItem:
    """Represents a single menu item."""

    def __init__(self, text, callback):
        self.text = text
        self.callback = callback


class SongMenuItem(MenuItem):
    """Menu item for songs with duration and download status."""

    def __init__(self, text, duration_sec, song_id, callback, downloaded=False):
        super().__init__(text, callback)
        self.duration_sec = duration_sec
        self.song_id = song_id
        self.downloaded = downloaded
        self.download_progress = 0  # 0-100

    def set_progress(self, progress):
        """Update download progress (0-100)."""
        self.download_progress = progress


class AlbumMenuItem(MenuItem):
    """Menu item for albums."""

    def __init__(self, text, album_id, callback):
        super().__init__(text, callback)
        self.album_id = album_id

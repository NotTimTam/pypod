import random
from typing import List, Optional
from ..models.song import Song


class QueueManager:
    def __init__(self):
        self.queue: List[Song] = []
        self.current_index: int = 0
        self.shuffle_enabled: bool = False
        self._original_indices: List[int] = []  # Track original order for shuffled queue

    def clear(self) -> None:
        """Clear queue and reset position."""
        self.queue = []
        self.current_index = 0
        self._original_indices = []

    def add_song(self, song: Song) -> None:
        """Add song to queue."""
        self.queue.append(song)

    def add_songs(self, songs: List[Song]) -> None:
        """Add multiple songs to queue."""
        self.queue.extend(songs)

    def queue_album(self, songs: List[Song]) -> None:
        """Clear queue and add all album songs, start at first."""
        self.clear()
        self.queue = songs.copy()
        self.current_index = 0

    def queue_artist(self, songs: List[Song]) -> None:
        """Clear queue and add all artist songs, start at first."""
        self.clear()
        self.queue = songs.copy()
        self.current_index = 0

    def queue_all_songs(self, songs: List[Song]) -> None:
        """Clear queue and add all songs from song list."""
        self.clear()
        self.queue = songs.copy()
        self.current_index = 0

    def set_shuffle(self, enabled: bool) -> None:
        """Enable/disable shuffle."""
        if enabled and not self.shuffle_enabled:
            # Enable shuffle: randomize queue but keep current song
            if self.queue:
                current_song = self.queue[self.current_index]
                remaining = self.queue[:self.current_index] + self.queue[self.current_index + 1 :]
                random.shuffle(remaining)
                self.queue = [current_song] + remaining
                self.current_index = 0
        elif not enabled and self.shuffle_enabled:
            # Disable shuffle: restore original order
            if self._original_indices:
                self.queue.sort(key=lambda s: self._original_indices[self.queue.index(s)])
                self.current_index = min(self.current_index, len(self.queue) - 1)

        self.shuffle_enabled = enabled

    def get_current_song(self) -> Optional[Song]:
        """Get currently playing song."""
        if 0 <= self.current_index < len(self.queue):
            return self.queue[self.current_index]
        return None

    def next(self) -> Optional[Song]:
        """Move to next song."""
        if self.current_index < len(self.queue) - 1:
            self.current_index += 1
            return self.get_current_song()
        return None

    def prev(self) -> Optional[Song]:
        """Move to previous song."""
        if self.current_index > 0:
            self.current_index -= 1
            return self.get_current_song()
        return None

    def is_at_end(self) -> bool:
        """Check if queue has finished."""
        return self.current_index >= len(self.queue) - 1 and len(self.queue) > 0

    def get_queue_position(self) -> tuple:
        """Get (current_index, queue_length)."""
        return (self.current_index, len(self.queue))

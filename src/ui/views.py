from typing import List, Callable, Optional
import pygame
from ..models.song import Song
from ..models.album import Album
from ..models.artist import Artist
from .renderer import Renderer


class View:
    """Base view class."""

    def __init__(self, renderer: Renderer):
        self.renderer = renderer
        self.selected_index = 0
        self.scroll_offset = 0

    def input(self, key: int) -> Optional[str]:
        """Handle input, return action string or None."""
        return None

    def render(self) -> None:
        """Render the view."""
        pass

    def set_content(self, *args, **kwargs) -> None:
        """Set view content before rendering."""
        pass

    def update_selection(self, index: int) -> None:
        """Update selected index with bounds checking."""
        self.selected_index = max(0, min(index, len(self.get_items()) - 1))
        self._update_scroll()

    def get_items(self) -> List[str]:
        """Get list of items to display."""
        return []

    def _update_scroll(self) -> None:
        """Update scroll offset to keep selection visible."""
        max_visible = 9
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_index - max_visible + 1


class MainMenuView(View):
    def __init__(self, renderer: Renderer):
        super().__init__(renderer)
        self.items = ["Artists", "Albums", "Songs", "Playlists", "Genres"]

    def get_items(self) -> List[str]:
        return self.items

    def input(self, key: int) -> Optional[str]:
        if key == pygame.K_UP:
            self.update_selection(self.selected_index - 1)
        elif key == pygame.K_DOWN:
            self.update_selection(self.selected_index + 1)
        elif key == pygame.K_RIGHT:
            return self.items[self.selected_index].lower()

        return None

    def render(self) -> None:
        self.renderer.clear()
        self.renderer.draw_header("PIPOD MUSIC")
        self.renderer.draw_list(self.items, 40, self.selected_index, max_items=5)


class ListMenuView(View):
    """Generic list view (Artists, Albums, Songs)."""

    def __init__(self, renderer: Renderer, title: str, display_format: Callable[[any], str] = None):
        super().__init__(renderer)
        self.title = title
        self.items_data: List[any] = []
        self.display_format = display_format or (lambda x: x.name if hasattr(x, "name") else str(x))

    def set_content(self, items: List[any]) -> None:
        self.items_data = items
        self.selected_index = 0
        self.scroll_offset = 0

    def get_items(self) -> List[str]:
        return [self.display_format(item) for item in self.items_data]

    def get_selected_item(self) -> Optional[any]:
        if 0 <= self.selected_index < len(self.items_data):
            return self.items_data[self.selected_index]
        return None

    def input(self, key: int) -> Optional[str]:
        if key == pygame.K_UP:
            self.update_selection(self.selected_index - 1)
        elif key == pygame.K_DOWN:
            self.update_selection(self.selected_index + 1)
        elif key == pygame.K_RIGHT:
            return "select"
        elif key == pygame.K_LEFT:
            return "back"

        return None

    def render(self) -> None:
        self.renderer.clear()
        self.renderer.draw_header(self.title)
        items_display = self.get_items()
        self.renderer.draw_list(items_display, 40, self.selected_index, offset=self.scroll_offset)


class NowPlayingView(View):
    def __init__(self, renderer: Renderer):
        super().__init__(renderer)
        self.song: Optional[Song] = None
        self.current_pos: int = 0
        self.total_songs: int = 0
        self.is_playing: bool = False
        self.shuffle_enabled: bool = False

    def set_content(self, song: Song, current_pos: int, total_songs: int, is_playing: bool, shuffle_enabled: bool):
        self.song = song
        self.current_pos = current_pos
        self.total_songs = total_songs
        self.is_playing = is_playing
        self.shuffle_enabled = shuffle_enabled

    def input(self, key: int) -> Optional[str]:
        if key == pygame.K_UP:
            return "prev"
        elif key == pygame.K_DOWN:
            return "next"
        elif key == pygame.K_RIGHT:
            return "toggle_pause"
        elif key == pygame.K_LEFT:
            return "back"

        return None

    def render(self) -> None:
        self.renderer.clear()
        if self.song:
            self.renderer.draw_now_playing_screen(
                self.song.title or self.song.filename,
                self.song.artist,
                self.song.album,
                self.current_pos,
                self.total_songs,
                self.is_playing,
                self.shuffle_enabled,
            )
        else:
            self.renderer.draw_centered_text("No song playing", 100)

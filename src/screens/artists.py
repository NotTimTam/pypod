from functools import partial
from pathlib import Path

from src.utils.screen import Screen
from src.utils.input import input_handler

from src.ui.menu import Menu
from src.ui.header import Header
from src.ui.control_icons import ControlIcons


class ArtistScreen(Screen):
    """Artists screen with navigation menu."""

    def __init__(self, state=None, request_screen=None, music_dir=None):
        super().__init__(
            padding_top=12,
            padding_bottom=12,
            padding_left=32,
            padding_right=32
        )
        self._request_screen = request_screen
        self._music_dir = Path(music_dir) if music_dir is not None else None

        menu_state = state.get("menu", {}) if state else {}
        self.header = Header(title="ARTISTS")
        self.menu = Menu(state=menu_state)
        self.controls = ControlIcons(icons={
            "x": "chevron-up.png",
            "y": "chevron-down.png",
            "a": "chevron-right.png",
            "b": "chevron-left.png",
        })
        self._setup_menu()

    def nullish(self):
        print(".")

    def _setup_menu(self):
        """Define menu items and their callbacks."""
        for index, artist_folder in enumerate(self._music_dir.iterdir()):
            if not artist_folder.is_dir():
                continue
            
            self.menu.add_item(
                artist_folder.name,
                partial(
                    self._request_screen,
                    "albums",
                    {
                        "artist_index": index,
                        "artist": artist_folder.name,
                        "return_index": 2,  # Artists is at index 2 in music menu
                    }
                )
            )

    def handle_input(self):
        """Handle input."""
        self.menu.handle_input()
        input_handler.handle_button("B", lambda: self._request_screen("music", {"menu": {"current_index": 2}}))

    def render(self, img, draw, font, width, height):
        """Render the screen with menu centered."""
        header_height = self.header.get_height(draw, font)

        content_width = width - self.padding_left - self.padding_right
        content_height = height - self.padding_top - self.padding_bottom
        menu_width = content_width - 8
        menu_height = content_height
        menu_x = self.padding_left + 4
        menu_y = self.padding_top + header_height

        self.header.render(img, draw, font)
        self.menu.render(img, draw, font, menu_x, menu_y, menu_width, menu_height)
        self.controls.render(img, draw)

    def get_state(self):
        """Return screen state for persistence."""
        return {
            "menu": self.menu.get_state()
        }

    def set_state(self, state):
        """Restore screen state from dict."""
        if state and "menu" in state:
            self.menu.set_state(state["menu"])
from functools import partial
from pathlib import Path

from src.utils.screen import Screen
from src.utils.input import input_handler
from src.utils.constants import AUDIO_EXTENSIONS

from src.ui.menu import Menu
from src.ui.header import Header
from src.ui.control_icons import ControlIcons

class SongScreen(Screen):
    """Songs screen with navigation menu."""

    def __init__(self, state=None, request_screen=None, music_dir=None):
        super().__init__(
            padding_top=12,
            padding_bottom=12,
            padding_left=32,
            padding_right=32
        )
        self._request_screen = request_screen
        self._music_dir = Path(music_dir) if music_dir is not None else None

        if (state):
            self._return_index = state.get("return_index", 0)
            self._return_screen = state.get("return_screen")
            self._from_artist = state.get("from_artist", False)
            self._artist = state.get('artist')

        menu_state = state.get("menu", {}) if state else {}
        self.header = Header(title=f"{state.get('album', 'SONGS') if state else 'SONGS'}")
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

        if self._artist and self._album:
            album_folder = self._music_dir / self._artist / self._album

            for file in album_folder.glob("*"):
                if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS:
                    # Add menu item for each song
                    self.menu.add_item(file.name, self.nullish)
                else:
                    continue
        else:
            print("not implemented")

    def handle_input(self):
        """Handle input."""
        self.menu.handle_input()
        input_handler.handle_button("B", lambda: self._request_screen(self._return_screen, {"menu": {"current_index": self._return_index, "artist": self._artist if self._from_artist else None }}))

    def render(self, img, draw, font, width, height):
        """Render the screen with menu centered."""
        # Calculate center position for menu
        header_height = self.header.get_height(draw, font)

        content_width = width - self.padding_left - self.padding_right
        content_height = height - self.padding_top - self.padding_bottom
        menu_width = content_width - 8
        menu_height = content_height
        menu_x = self.padding_left + 4
        menu_y = self.padding_top + header_height

        # Render header
        self.header.render(img, draw, font)

        # Render menu
        self.menu.render(img, draw, font, menu_x, menu_y, menu_width, menu_height)

        # Render controls
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

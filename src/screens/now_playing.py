from functools import partial
from pathlib import Path

from src.utils.screen import Screen
from src.utils.input import input_handler
from src.utils.constants import AUDIO_EXTENSIONS
from src.utils.media_player import SongItem

from src.ui.menu import Menu
from src.ui.header import Header
from src.ui.control_icons import ControlIcons

class NowPlayingScreen(Screen):
    """Now playing screen with navigation menu."""

    def __init__(self, state=None, request_screen=None, music_dir=None, media_player=None):
        super().__init__(
            padding_top=12,
            padding_bottom=12,
            padding_left=32,
            padding_right=32
        )
        self._request_screen = request_screen
        self._music_dir = Path(music_dir) if music_dir is not None else None
        self._media_player = media_player

        if state:
            self._return_index = state.get("return_index", 0)
            self._return_screen = state.get("return_screen")

        self.controls = ControlIcons(icons={
            "x": "skip-back.png",
            "y": "skip-forward.png",
            "a": "play.png",
            "b": "chevron-left.png",
        })
        self._setup_screen()

    def nullish(self):
        print(".")

    def _setup_screen(self):
        """Define screen items and their callbacks."""

    def handle_input(self):
        """Handle input."""
        def go_back():
            self._request_screen(self._return_screen, {
                "menu": {"current_index": self._return_index or 0},
            })
        
        input_handler.handle_button("B", go_back)

    def render(self, img, draw, font, width, height):
        """Render the screen with menu centered."""
        content_width = width - self.padding_left - self.padding_right
        content_height = height - self.padding_top - self.padding_bottom
        # menu_width = content_width - 8
        # menu_height = content_height
        # menu_x = self.padding_left + 4
        # menu_y = self.padding_top + header_height

        self.controls.render(img, draw)

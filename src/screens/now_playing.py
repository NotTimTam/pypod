from functools import partial
from pathlib import Path

from src.utils.screen import Screen
from src.utils.input import input_handler

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
        input_handler.handle_button("B", partial(self._request_screen, "home"))

    def render(self, img, draw, font, width, height):
        """Render the screen with menu centered."""
        if (not self._media_player.current_song): return None

        draw.text((self.padding_left, self.padding_top), self._media_player.current_song.name, fill=(255, 255, 255), font=font)

        self.controls.render(img, draw)

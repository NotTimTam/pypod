from functools import partial

from src.utils.screen import Screen
from src.utils.input import input_handler

from src.ui.menu import Menu
from src.ui.header import Header
from src.ui.control_icons import ControlIcons


class MusicScreen(Screen):
    """Music screen with navigation menu."""

    def __init__(self, state=None, request_screen=None):
        super().__init__(
            padding_top=12,
            padding_bottom=12,
            padding_left=32,
            padding_right=32
        )

        self._request_screen = request_screen

        menu_state = state.get("menu", {}) if state else {}
        self.header = Header(title="MUSIC")
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
        # Menu indices for reference:
        # 0: Shuffle Songs
        # 1: Playlists
        # 2: Artists
        # 3: Albums
        # 4: Songs
        
        self.menu.add_item("Shuffle Songs", self.nullish)
        self.menu.add_item("Playlists >", self.nullish)
        self.menu.add_item("Artists >", partial(self._request_screen, "artists", {"return_index": 2}))
        self.menu.add_item("Albums >", partial(self._request_screen, "albums", {"return_index": 3, "from_artist": False}))
        self.menu.add_item("Songs >", partial(self._request_screen, "songs", {"return_index": 4, "return_screen": "music"}))
        # self.menu.add_item("Podcasts >", self.nullish)
        # self.menu.add_item("Genres >", self.nullish)
        # self.menu.add_item("Audiobooks >", self.nullish)

    def handle_input(self):
        """Handle input."""
        self.menu.handle_input()
        input_handler.handle_button("B", lambda: self._request_screen("home", {"menu": {"current_index": 0}}))

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
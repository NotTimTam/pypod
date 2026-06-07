from functools import partial
from pathlib import Path

from src.utils.screen import Screen
from src.utils.input import input_handler

from src.ui.menu import Menu
from src.ui.header import Header
from src.ui.control_icons import ControlIcons


class AlbumScreen(Screen):
    """Albums screen with navigation menu."""

    def __init__(
        self, state=None, request_screen=None, music_dir=None, media_player=None
    ):
        super().__init__(
            padding_top=12, padding_bottom=12, padding_left=32, padding_right=32
        )

        self._request_screen = request_screen
        self._music_dir = Path(music_dir) if music_dir is not None else None
        self._media_player = media_player

        # Initialize attributes
        self._artist_index = 0
        self._return_index = 3  # Default to albums position in music menu
        self._return_screen = "music"
        self._artist = None
        self._from_artist = False  # Track if we're in artist-specific view

        if state:
            self._artist_index = state.get("artist_index", 0)
            self._return_index = state.get("return_index", 3)
            self._artist = state.get("artist")
            self._from_artist = state.get("from_artist", False)
            # If we came from artist view, return to artists; otherwise return to music
            self._return_screen = "artists" if self._from_artist else "music"

        menu_state = state.get("menu", {}) if state else {}

        # FIX: Header shows artist name ONLY if we're in artist-specific view
        # If we're viewing all albums from music, show "ALBUMS" regardless of current selection
        header_title = self._artist if self._from_artist else "ALBUMS"
        self.header = Header(title=header_title)

        self.menu = Menu(state=menu_state)
        self.controls = ControlIcons(
            icons={
                "x": "chevron-up.png",
                "y": "chevron-down.png",
                "a": "chevron-right.png",
                "b": "chevron-left.png",
            }
        )
        self._setup_menu()

    def _setup_menu(self):
        """Define menu items and their callbacks."""
        if self._from_artist:
            # Viewing albums for a specific artist
            artist_folder = self._music_dir / self._artist

            for index, album_folder in enumerate(artist_folder.iterdir()):
                if not album_folder.is_dir():
                    continue

                self.menu.add_item(
                    album_folder.name,
                    partial(
                        self._request_screen,
                        "songs",
                        {
                            "artist_index": self._artist_index,
                            "album_index": index,
                            "album": album_folder.name,
                            "artist": self._artist,
                            "from_artist": True,
                            "return_screen": "albums",
                            "return_index": index,
                        },
                    ),
                )
        else:
            # Viewing all albums across all artists (from music)
            index = 0
            for artist_folder in self._music_dir.iterdir():
                if not artist_folder.is_dir():
                    continue

                for album_folder in artist_folder.iterdir():
                    if not album_folder.is_dir():
                        continue

                    self.menu.add_item(
                        album_folder.name,
                        partial(
                            self._request_screen,
                            "songs",
                            {
                                "artist_index": 0,
                                "album_index": index,
                                "album": album_folder.name,
                                "artist": artist_folder.name,
                                "from_artist": False,
                                "return_screen": "albums",
                                "return_index": index,
                            },
                        ),
                    )
                    index += 1

    def handle_input(self):
        """Handle input."""
        self.menu.handle_input()

        def go_back():
            return_state = {
                "menu": {
                    "current_index": self._artist_index
                    if self._from_artist
                    else self._return_index
                }
            }
            # Always preserve the from_artist flag and artist info when returning to artist screen
            if self._from_artist:
                return_state["from_artist"] = True
                return_state["artist_index"] = self._artist_index

            self._request_screen(self._return_screen, return_state)

        input_handler.handle_button("B", go_back)

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
        return {"menu": self.menu.get_state()}

    def set_state(self, state):
        """Restore screen state from dict."""
        if state and "menu" in state:
            self.menu.set_state(state["menu"])

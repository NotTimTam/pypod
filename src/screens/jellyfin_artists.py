import threading
from functools import partial

from src.utils.screen import Screen
from src.utils.input import input_handler

from src.ui.menu import Menu
from src.ui.header import Header
from src.ui.control_icons import ControlIcons


class JellyfinArtistsScreen(Screen):
    def __init__(self, state=None, request_screen=None, jellyfin=None, download_manager=None):
        super().__init__(padding_top=12, padding_bottom=12, padding_left=32, padding_right=32)
        self._request_screen = request_screen
        self._jellyfin = jellyfin
        self._download_manager = download_manager

        self.header = Header(title="ARTISTS")
        self.menu = Menu(state=state.get("menu", {}) if state else {})
        self.controls = ControlIcons(icons={"x": "chevron-up.png", "y": "chevron-down.png", "a": "chevron-right.png", "b": "chevron-left.png"})

        self.artists = []
        self._loading = True
        self._load_artists_async()

    def _load_artists_async(self):
        def load():
            try:
                if self._jellyfin:
                    self.artists = self._jellyfin.get_artists()
                    self._populate_menu()
            except Exception as e:
                print(f"Artists load error: {e}")
            finally:
                self._loading = False

        threading.Thread(target=load, daemon=True).start()

    def _populate_menu(self):
        self.menu.items.clear()
        for artist in self.artists:
            callback = partial(self._on_artist_selected, artist["Id"], artist["Name"])
            self.menu.items.append(MenuItem(artist["Name"], callback))

    def _on_artist_selected(self, artist_id, artist_name):
        state = {
            "artist_id": artist_id,
            "artist_name": artist_name,
            "parent_screen": "jellyfin_artists",
            "menu": {"current_index": self.menu.current_index}
        }
        self._request_screen("jellyfin_albums", state)

    def handle_input(self):
        self.menu.handle_input()
        input_handler.handle_button("B", lambda: self._request_screen("jellyfin"))

    def render(self, img, draw, font, width, height):
        self.header.render(img, draw, font, width)
        self.menu.render(img, draw, font, width, height)
        self.controls.render(img, draw, width, height)
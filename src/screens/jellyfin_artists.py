import threading
from functools import partial

from src.utils.screen import Screen
from src.utils.input import input_handler

from src.ui.menu import Menu
from src.ui.header import Header
from src.ui.control_icons import ControlIcons


class JellyfinArtistsScreen(Screen):
    """Jellyfin Artists screen with list of all artists."""

    def __init__(self, state=None, request_screen=None, jellyfin=None, download_manager=None):
        super().__init__(
            padding_top=12,
            padding_bottom=12,
            padding_left=32,
            padding_right=32
        )
        self._request_screen = request_screen
        self._jellyfin = jellyfin
        self._download_manager = download_manager

        menu_state = state.get("menu", {}) if state else {}
        self.header = Header(title="ARTISTS")
        self.menu = Menu(state=menu_state)
        self.controls = ControlIcons(icons={
            "x": "chevron-up.png",
            "y": "chevron-down.png",
            "a": "chevron-right.png",
            "b": "chevron-left.png",
        })

        self.artists = []
        self._loading = True
        self._load_artists_async()

    def _load_artists_async(self):
        """Load artists in background thread."""
        def load():
            try:
                if self._jellyfin:
                    self.artists = self._jellyfin.get_artists()
                    self._populate_menu()
            except Exception as e:
                print(f"Error loading artists: {e}")
            finally:
                self._loading = False

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def _populate_menu(self):
        """Populate menu with artists."""
        for artist in self.artists:
            callback = partial(
                self._on_artist_selected,
                artist["Id"],
                artist["Name"]
            )
            self.menu.add_item(f"{artist['Name']} >", callback)

    def _on_artist_selected(self, artist_id, artist_name):
        """Handle artist selection - navigate to albums for this artist."""
        self._request_screen("jellyfin_albums", {
            "menu": {"current_index": 0},
            "artist_id": artist_id,
            "artist_name": artist_name,
            "parent_screen": "jellyfin_artists",
        })

    def _go_back(self):
        """Navigate back to Jellyfin main screen."""
        self._request_screen("jellyfin", {"menu": {"current_index": 0}})

    def handle_input(self):
        """Handle input."""
        self.menu.handle_input()
        input_handler.handle_button("B", self._go_back)

    def render(self, img, draw, font, width, height):
        """Render the screen."""
        header_height = self.header.get_height(draw, font)

        content_width = width - self.padding_left - self.padding_right
        content_height = height - self.padding_top - self.padding_bottom
        menu_width = content_width - 8
        menu_height = content_height
        menu_x = self.padding_left + 4
        menu_y = self.padding_top + header_height

        # Render header
        self.header.render(img, draw, font)

        # Show loading indicator if still loading
        if self._loading and not self.artists:
            loading_text = "Loading artists..."
            bbox = draw.textbbox((0, 0), loading_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = int((width - text_width) / 2)
            text_y = menu_y + 20
            draw.text((text_x, text_y), loading_text, fill=(255, 255, 255), font=font)
        else:
            # Render menu
            self.menu.render(img, draw, font, menu_x, menu_y, menu_width, menu_height, self._download_manager)

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

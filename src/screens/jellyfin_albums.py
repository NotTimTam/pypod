import threading
from functools import partial

from src.utils.screen import Screen
from src.utils.input import input_handler

from src.ui.menu import Menu
from src.ui.header import Header
from src.ui.control_icons import ControlIcons


class JellyfinAlbumsScreen(Screen):
    """Jellyfin Albums screen - can show all albums or albums by artist."""

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

        # Extract state
        self.artist_id = state.get("artist_id") if state else None
        self.artist_name = state.get("artist_name") if state else None
        self.parent_screen = state.get("parent_screen", "jellyfin") if state else "jellyfin"

        menu_state = state.get("menu", {}) if state else {}

        # Set title based on context
        if self.artist_id:
            title = f"{self.artist_name}"
        else:
            title = "ALBUMS"

        self.header = Header(title=title)
        self.menu = Menu(state=menu_state)
        self.controls = ControlIcons(icons={
            "x": "chevron-up.png",
            "y": "chevron-down.png",
            "a": "chevron-right.png",
            "b": "chevron-left.png",
        })

        self.albums = []
        self._loading = True
        self._load_albums_async()

    def _load_albums_async(self):
        """Load albums in background thread."""
        def load():
            try:
                if self._jellyfin:
                    self.albums = self._jellyfin.get_albums(artist_id=self.artist_id)
                    self._populate_menu()
            except Exception as e:
                print(f"Error loading albums: {e}")
            finally:
                self._loading = False

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def _populate_menu(self):
        """Populate menu with albums."""
        for album in self.albums:
            callback = partial(
                self._on_album_selected,
                album["Id"],
                album["Name"]
            )
            self.menu.add_item(f"{album['Name']} >", callback)

    def _on_album_selected(self, album_id, album_name):
        """Handle album selection - navigate to songs for this album."""
        self._request_screen("jellyfin_songs", {
            "menu": {"current_index": 0},
            "album_id": album_id,
            "album_name": album_name,
            "parent_screen": "jellyfin_albums",
            "parent_state": self.get_state(),
        })

    def _go_back(self):
        """Navigate back to parent screen."""
        if self.parent_screen == "jellyfin_artists":
            self._request_screen("jellyfin_artists", {"menu": {"current_index": 0}})
        else:
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
        if self._loading and not self.albums:
            loading_text = "Loading albums..."
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
            "menu": self.menu.get_state(),
            "artist_id": self.artist_id,
            "artist_name": self.artist_name,
            "parent_screen": self.parent_screen,
        }

    def set_state(self, state):
        """Restore screen state from dict."""
        if state and "menu" in state:
            self.menu.set_state(state["menu"])

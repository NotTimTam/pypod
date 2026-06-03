import threading
from functools import partial

from src.utils.screen import Screen
from src.utils.input import input_handler

from src.ui.menu import Menu
from src.ui.menu_items import SongMenuItem, AlbumMenuItem
from src.ui.header import Header
from src.ui.control_icons import ControlIcons


class JellyfinSongsScreen(Screen):
    """Jellyfin Songs screen with advanced download functionality."""

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

        # Extract navigation state for history
        self.album_id = state.get("album_id") if state else None
        self.album_name = state.get("album_name", "Album") if state else "Album"
        self.parent_screen = state.get("parent_screen", "jellyfin_albums") if state else "jellyfin_albums"
        self.parent_state = state.get("parent_state") if state else None

        menu_state = state.get("menu", {}) if state else {}

        self.header = Header(title=self.album_name[:20])  # Truncate if too long
        self.menu = Menu(state=menu_state)
        self.controls = ControlIcons(icons={
            "x": "chevron-up.png",
            "y": "chevron-down.png",
            "a": "play.png",  # Or download icon if preferred
            "b": "chevron-left.png",
        })

        self.songs = []
        self._loading = True
        self._error_message = None
        self._download_in_progress = False
        self._load_songs_async()

    def _load_songs_async(self):
        """Load songs in background thread."""
        def load():
            try:
                if self._jellyfin and self.album_id:
                    self.songs = self._jellyfin.get_songs(album_id=self.album_id)
                    self._populate_menu()
            except Exception as e:
                print(f"Error loading songs: {e}")
                self._error_message = str(e)
            finally:
                self._loading = False

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def _populate_menu(self):
        """Populate menu with album download button + songs. Reuses logic cleanly."""
        self.menu.items.clear()  # Clean slate

        # "Download full album" button (first item)
        album_callback = partial(self._on_download_album)
        album_item = AlbumMenuItem(
            "↓ Download Full Album",
            self.album_id,
            album_callback
        )
        self.menu.items.append(album_item)

        # Songs list
        for song in self.songs:
            duration_ticks = song.get("Duration", 0)
            duration_sec = int(duration_ticks / 10000000) if duration_ticks else 0
            song_id = song.get("Id")
            song_name = song.get("Name", "Unknown Song")

            downloaded = self._is_song_downloaded(song_id, song_name)
            callback = partial(self._on_song_selected, song_id, song_name)

            song_item = SongMenuItem(
                song_name,
                duration_sec,
                song_id,
                callback,
                downloaded=downloaded
            )
            self.menu.items.append(song_item)

    def _is_song_downloaded(self, song_id, song_name):
        """More robust check for downloaded status."""
        if not self._jellyfin or not self._jellyfin.download_root:
            return False
        try:
            # Look in expected artist/album structure
            root = self._jellyfin.download_root
            for artist_dir in root.iterdir():
                if not artist_dir.is_dir():
                    continue
                for album_dir in artist_dir.iterdir():
                    if not album_dir.is_dir():
                        continue
                    # Check for song by ID or name
                    for f in album_dir.glob("*.mp3"):  # Adjust extension as needed
                        if song_id in f.name or song_name.lower() in f.name.lower():
                            return True
        except Exception:
            pass
        return False

    def _on_download_album(self):
        """Download entire album."""
        if not self._download_manager or self._download_manager.is_downloading():
            self._error_message = "Download in progress or unavailable"
            return
        if self._download_manager.start_download(self.album_id, is_album=True):
            self._download_in_progress = True
            self._error_message = None
        else:
            self._error_message = "Failed to start album download"

    def _on_song_selected(self, song_id, song_name):
        """Download individual song."""
        if not self._download_manager or self._download_manager.is_downloading():
            self._error_message = "Download in progress or unavailable"
            return
        if self._download_manager.start_download(song_id, is_album=False):
            self._download_in_progress = True
            self._error_message = None
        else:
            self._error_message = "Failed to start song download"

    def _go_back(self):
        """Navigate back with full history preservation."""
        if self.parent_state:
            self._request_screen(self.parent_screen, self.parent_state)
        else:
            self._request_screen("jellyfin_albums", {"menu": {"current_index": 0}})

    def handle_input(self):
        """Handle input with download lock."""
        download_state = self._download_manager.get_state() if self._download_manager else None

        if download_state and download_state["current_status"] == "downloading":
            # Block most input during active download
            return

        if download_state and download_state["current_status"] == "failed":
            # Allow back on failure
            input_handler.handle_button("B", self._go_back)
            # Could add A for retry later
            return

        # Normal navigation
        self.menu.handle_input()
        input_handler.handle_button("B", self._go_back)

    def render(self, img, draw, font, width, height):
        """Render with download feedback."""
        header_height = self.header.get_height(draw, font)

        content_width = width - self.padding_left - self.padding_right
        content_height = height - self.padding_top - self.padding_bottom
        menu_width = content_width - 8
        menu_height = content_height
        menu_x = self.padding_left + 4
        menu_y = self.padding_top + header_height

        self.header.render(img, draw, font)

        if self._loading and not self.songs:
            loading_text = "Loading songs..."
            bbox = draw.textbbox((0, 0), loading_text, font=font)
            text_x = int((width - (bbox[2] - bbox[0])) / 2)
            text_y = menu_y + 30
            draw.text((text_x, text_y), loading_text, fill=(255, 255, 255), font=font)
        elif self._error_message:
            err_text = f"Error: {self._error_message[:30]}"
            bbox = draw.textbbox((0, 0), err_text, font=font)
            text_x = int((width - (bbox[2] - bbox[0])) / 2)
            draw.text((text_x, menu_y + 20), err_text, fill=(255, 100, 100), font=font)
            self.menu.render(img, draw, font, menu_x, menu_y + 50, menu_width, menu_height - 50, self._download_manager)
        else:
            self.menu.render(img, draw, font, menu_x, menu_y, menu_width, menu_height, self._download_manager)

        self.controls.render(img, draw)

    def get_state(self):
        return {
            "menu": self.menu.get_state(),
            "album_id": self.album_id,
            "album_name": self.album_name,
            "parent_screen": self.parent_screen,
            "parent_state": self.parent_state
        }

    def set_state(self, state):
        if state and "menu" in state:
            self.menu.set_state(state["menu"])
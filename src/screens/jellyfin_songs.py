import threading
from pathlib import Path
from functools import partial

from src.utils.screen import Screen
from src.utils.input import input_handler
from src.utils.constants import SCREEN_SIZE

from src.ui.menu import Menu
from src.ui.menu_items import SongMenuItem, AlbumMenuItem
from src.ui.header import Header
from src.ui.control_icons import ControlIcons


class JellyfinSongsScreen(Screen):
    """Jellyfin Songs screen with download functionality."""

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
        self.album_id = state.get("album_id") if state else None
        self.album_name = state.get("album_name", "Album") if state else "Album"
        self.parent_screen = state.get("parent_screen", "jellyfin_albums") if state else "jellyfin_albums"
        self.parent_state = state.get("parent_state") if state else None

        menu_state = state.get("menu", {}) if state else {}

        self.header = Header(title=self.album_name)
        self.menu = Menu(state=menu_state)
        self.controls = ControlIcons(icons={
            "x": "chevron-up.png",
            "y": "chevron-down.png",
            "a": "download.png",
            "b": "chevron-left.png",
        })

        self.songs = []
        self._loading = True
        self._load_songs_async()
        self._error_message = None

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
        """Populate menu with album download button and songs."""
        # Add download full album button
        album_callback = partial(self._on_download_album)
        album_item = AlbumMenuItem(
            "↓ Download Album",
            self.album_id,
            album_callback
        )
        self.menu.items.append(album_item)

        # Add songs
        for song in self.songs:
            duration = song.get("RunTimeTicks", 0) // 10000000 if song.get("RunTimeTicks") else 0  # Jellyfin uses ticks
            song_id = song.get("Id")
            downloaded = self._is_song_downloaded(song.get("Name"))

            callback = partial(self._on_song_selected, song_id, song.get("Name"))
            song_item = SongMenuItem(
                song.get("Name", "Unknown"),
                duration,
                song_id,
                callback,
                downloaded=downloaded
            )
            self.menu.items.append(song_item)

    def _is_song_downloaded(self, song_name):
        """Check if a song is already downloaded."""
        if not self._jellyfin or not self._jellyfin.download_root:
            return False

        # Check if file exists in artist/album folder
        for artist_folder in self._jellyfin.download_root.iterdir():
            if not artist_folder.is_dir():
                continue
            for album_folder in artist_folder.iterdir():
                if not album_folder.is_dir():
                    continue
                # Check if any file with similar name exists
                for file in album_folder.glob("*"):
                    if file.is_file() and Path(file.name).stem == song_name:
                        # Very basic check - in production would verify exact song
                        return True
        return False

    def _on_download_album(self):
        """Handle download full album button."""
        if not self._download_manager:
            self._error_message = "Download manager not available"
            return

        if self._download_manager.is_downloading():
            self._error_message = "Already downloading"
            return

        if self._download_manager.start_download(self.album_id, is_album=True):
            self._error_message = None
        else:
            self._error_message = "Failed to start download"

    def _on_song_selected(self, song_id, song_name):
        """Handle song selection - download it."""
        if not self._download_manager:
            self._error_message = "Download manager not available"
            return

        if self._download_manager.is_downloading():
            self._error_message = "Already downloading"
            return

        if self._download_manager.start_download(song_id, is_album=False):
            self._error_message = None
        else:
            self._error_message = "Failed to start download"

    def _go_back(self):
        """Navigate back to albums screen."""
        if self.parent_state:
            self._request_screen(self.parent_screen, self.parent_state)
        else:
            self._request_screen("jellyfin_albums", {"menu": {"current_index": 0}})

    def handle_input(self):
        """Handle input - restrict navigation if downloading."""
        download_state = None
        if self._download_manager:
            download_state = self._download_manager.get_state()

        # Only allow back button and retry during failed download
        if download_state and download_state["current_status"] == "failed":
            input_handler.handle_button("B", self._go_back)
            # Could add retry button here
            return

        # Prevent any navigation during active download
        if download_state and download_state["current_download_id"]:
            # Allow B button to see the download status
            return

        # Normal menu handling when not downloading
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
        if self._loading and not self.songs:
            loading_text = "Loading songs..."
            bbox = draw.textbbox((0, 0), loading_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = int((width - text_width) / 2)
            text_y = menu_y + 20
            draw.text((text_x, text_y), loading_text, fill=(255, 255, 255), font=font)
        else:
            # Render menu with download manager for progress tracking
            self.menu.render(img, draw, font, menu_x, menu_y, menu_width, menu_height, self._download_manager)

        # Render download status and error messages
        self._render_download_status(draw, font, header_height)

        # Render controls
        self.controls.render(img, draw)

    def _render_download_status(self, draw, font, header_height):
        """Render download status messages and prevent navigation indicators."""
        if not self._download_manager:
            return

        download_state = self._download_manager.get_state()

        if download_state["current_status"] == "downloading" and download_state["current_download_id"]:
            status_text = f"Downloading: {download_state['current_progress']}%"
            draw.rectangle((0,0, SCREEN_SIZE, header_height), fill=(0, 0, 0))
            draw.text((self.padding_left + 4, 4), status_text, fill=(0, 255, 0), font=font)

        # Show error message
        if self._error_message:
            error_text = f"Error: {self._error_message[:50]}"
            print(error_text)
            draw.rectangle((0,0, SCREEN_SIZE, header_height), fill=(0, 0, 0))
            draw.text((self.padding_left + 4, 4), error_text, fill=(255, 0, 0), font=font)
        elif download_state["current_status"] == "failed" and download_state["error_message"]:
            error_text = f"Download failed: {download_state['error_message'][:40]}"
            print(error_text)
            draw.rectangle((0,0, SCREEN_SIZE, header_height), fill=(0, 0, 0))
            draw.text((self.padding_left + 4, 4), error_text, fill=(255, 0, 0), font=font)

    def get_state(self):
        """Return screen state for persistence."""
        return {
            "menu": self.menu.get_state(),
            "album_id": self.album_id,
            "album_name": self.album_name,
            "parent_screen": self.parent_screen,
            "parent_state": self.parent_state,
        }

    def set_state(self, state):
        """Restore screen state from dict."""
        if state and "menu" in state:
            self.menu.set_state(state["menu"])

from functools import partial
from pathlib import Path

from src.utils.screen import Screen
from src.utils.input import input_handler
from src.utils.constants import AUDIO_EXTENSIONS
from src.utils.media_player import SongItem

from src.ui.menu import Menu
from src.ui.header import Header
from src.ui.control_icons import ControlIcons

class SongScreen(Screen):
    """Songs screen with navigation menu."""

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

        # Initialize all attributes before using them
        self._artist_index = None
        self._album_index = None
        self._return_index = None
        self._return_screen = None
        self._from_artist = False
        self._artist = None
        self._album = None

        if state:
            self._artist_index = state.get("artist_index")
            self._album_index = state.get("album_index")
            self._return_index = state.get("return_index", 0)
            self._return_screen = state.get("return_screen")
            self._from_artist = state.get("from_artist", False)
            self._artist = state.get('artist')
            self._album = state.get('album')

        menu_state = state.get("menu", {}) if state else {}
        album_title = self._album if self._album else "SONGS"
        self.header = Header(title=album_title)
        
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
        self.menu.add_item("Play All", self.nullish)
        self.menu.add_item("Queue All", self.nullish)

        if self._artist and self._album:
            album_folder = self._music_dir / self._artist / self._album

            for file in album_folder.glob("*"):
                if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS:
                    print("IMPLEMENT QUEUE/PLAY DIALOGUE")
                    song_item = self._media_player.create_song_item(file.name, self._album, self._artist)
                    callback = partial(self._media_player.play_song, song_item)
                    self.menu.add_item(file.stem, callback)
        else:
            for artist_folder in self._music_dir.iterdir():
                if not artist_folder.is_dir():
                    continue
                
                for album_folder in artist_folder.iterdir():
                    if not album_folder.is_dir():
                        continue
             
                    for file in album_folder.glob("*"):
                        if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS:
                            song_item = self._media_player.create_song_item(file.name, self._album, self._artist)
                            callback = partial(self._media_player.play_song, song_item)
                            self.menu.add_item(file.stem + " / " + album_folder.name + " / " + artist_folder.name, callback)

    def handle_input(self):
        """Handle input."""
        self.menu.handle_input()
        
        # FIX: Pass complete state needed for the return screen
        def go_back():
            return_state = {
                "menu": {"current_index": self._album_index if self._return_screen == "albums" else self._return_index},
            }
            
            # If returning to albums, pass context about how we got there
            if self._return_screen == "albums":
                return_state["artist"] = self._artist  # Always include artist name (or None)
                return_state["artist_index"] = self._artist_index
                return_state["from_artist"] = self._from_artist  # Critical: tells albums if header should show artist or "ALBUMS"
            
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
        return {
            "menu": self.menu.get_state()
        }

    def set_state(self, state):
        """Restore screen state from dict."""
        if state and "menu" in state:
            self.menu.set_state(state["menu"])
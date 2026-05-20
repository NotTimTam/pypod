from typing import Optional, List, Tuple
from .renderer import Renderer
from .views import MainMenuView, ListMenuView, NowPlayingView, View
from ..models.song import Song
from ..models.album import Album
from ..models.artist import Artist
from ..utils.image_handler import get_folder_image


class UIManager:
    def __init__(self, renderer: Renderer, songs: List[Song], albums: List[Album], artists: List[Artist]):
        self.renderer = renderer
        self.songs = songs
        self.albums = albums
        self.artists = artists

        # Initialize views
        self.main_menu = MainMenuView(renderer)
        self.artists_view = ListMenuView(renderer, "ARTISTS", lambda a: a.display_name())
        self.albums_view = ListMenuView(renderer, "ALBUMS", lambda a: a.display_name(include_artist=True))
        self.songs_view = ListMenuView(renderer, "SONGS", lambda s: s.display_name(include_artist=True))
        self.now_playing = NowPlayingView(renderer)

        # State tracking
        self.current_view: View = self.main_menu
        self.view_stack: List[Tuple[View, any]] = []  # Track navigation history

        # Populate artists list
        self.artists_view.set_content(artists)

    def render(self) -> None:
        """Render current view."""
        self.current_view.render()

    def handle_input(self, key: int) -> Optional[str]:
        """Handle keyboard input and dispatch actions. Returns action name or None."""
        action = self.current_view.input(key)

        if action is None:
            return None

        if action == "back":
            self._go_back()
        elif action == "select":
            self._handle_select()
        elif action == "artists":
            self._open_artists()
        elif action == "albums":
            self._open_all_albums()
        elif action == "songs":
            self._open_all_songs()
        elif action == "playlists":
            pass  # TODO
        elif action == "genres":
            pass  # TODO

        return action

    def _go_back(self) -> None:
        """Go back to previous view."""
        if self.view_stack:
            self.current_view, _ = self.view_stack.pop()
        else:
            self.current_view = self.main_menu

    def _handle_select(self) -> None:
        """Handle selection in current view."""
        if self.current_view == self.artists_view:
            self._open_artist_albums()
        elif self.current_view == self.albums_view:
            self._open_album_songs()
        elif self.current_view == self.songs_view:
            self._play_song()

    def _open_artists(self) -> None:
        """Open artists list."""
        self.view_stack.append((self.current_view, None))
        self.current_view = self.artists_view
        self.artists_view.selected_index = 0

    def _open_artist_albums(self) -> None:
        """Open albums for selected artist."""
        artist = self.artists_view.get_selected_item()
        if not artist:
            return

        # Get album objects for this artist
        artist_albums = [self.albums[i] for i in artist.album_ids]
        artist_albums.sort(key=lambda a: a.name)

        self.view_stack.append((self.current_view, artist))
        self.albums_view.set_content(artist_albums)
        self.current_view = self.albums_view

        # Set background image if available
        image_bytes = get_folder_image(artist.path)
        self.renderer.set_background_image(image_bytes)

    def _open_all_albums(self) -> None:
        """Open all albums."""
        albums_sorted = sorted(self.albums, key=lambda a: a.name)
        self.view_stack.append((self.current_view, None))
        self.albums_view.set_content(albums_sorted)
        self.current_view = self.albums_view

    def _open_album_songs(self) -> None:
        """Open songs for selected album."""
        album = self.albums_view.get_selected_item()
        if not album:
            return

        # Get song objects for this album
        album_songs = [self.songs[i] for i in album.song_ids]

        self.view_stack.append((self.current_view, album))
        self.songs_view.set_content(album_songs)
        self.current_view = self.songs_view

        # Set background image if available
        image_bytes = get_folder_image(album.path)
        if image_bytes:
            self.renderer.set_background_image(image_bytes)
        else:
            # Try album artist folder
            artist = next((a for a in self.artists if a.name == album.artist), None)
            if artist:
                image_bytes = get_folder_image(artist.path)
                self.renderer.set_background_image(image_bytes)

    def _open_all_songs(self) -> None:
        """Open all songs."""
        songs_sorted = sorted(self.songs, key=lambda s: s.title or s.filename)
        self.view_stack.append((self.current_view, None))
        self.songs_view.set_content(songs_sorted)
        self.current_view = self.songs_view

    def _play_song(self) -> None:
        """Play selected song (will be handled by main loop)."""
        pass

    def switch_to_now_playing(self, song: Song, current_pos: int, total_songs: int, is_playing: bool, shuffle_enabled: bool) -> None:
        """Switch to now playing view."""
        self.view_stack.append((self.current_view, None))
        self.now_playing.set_content(song, current_pos, total_songs, is_playing, shuffle_enabled)
        self.current_view = self.now_playing

        # Set background from song metadata or album
        album = next((a for a in self.albums if a.name == song.album and a.artist == song.artist), None)
        image_bytes = None
        if album:
            image_bytes = get_folder_image(album.path)

        # Fallback to artist folder image if no album image available
        if not image_bytes:
            artist = next((a for a in self.artists if a.name == song.artist), None)
            if artist:
                image_bytes = get_folder_image(artist.path)

        self.renderer.set_background_image(image_bytes)

    def update_now_playing(self, song: Song, current_pos: int, total_songs: int, is_playing: bool, shuffle_enabled: bool) -> None:
        """Update now playing view (when skipping songs, etc)."""
        if self.current_view == self.now_playing:
            self.now_playing.set_content(song, current_pos, total_songs, is_playing, shuffle_enabled)

    def get_selected_song_for_play(self) -> Optional[Song]:
        """Get currently selected song to play."""
        if self.current_view == self.songs_view:
            return self.songs_view.get_selected_item()
        return None

    def draw_now_playing(self, song: Song) -> None:
        """Draw now playing when audio is playing."""
        self.renderer.draw_now_playing(song.title or song.filename, song.artist)

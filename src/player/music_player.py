from typing import Optional, Callable, List
import time

try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False


class MusicPlayer:
    def __init__(self):
        self.instance: Optional[vlc.Instance] = None
        self.player: Optional[vlc.MediaListPlayer] = None
        self.media_list: Optional[vlc.MediaList] = None
        self.is_playing: bool = False
        self.current_file: Optional[str] = None

        if VLC_AVAILABLE:
            try:
                self.instance = vlc.Instance("--quiet", "--no-video")
                self.player = self.instance.media_list_player_new()
                self.media_list = self.instance.media_list_new()
            except Exception as e:
                pass

    def load_file(self, file_path: str) -> bool:
        """Load a single audio file."""
        if not VLC_AVAILABLE or not self.player or not self.instance:
            return False

        try:
            self.media_list = self.instance.media_list_new()
            media = self.instance.media_new(file_path)
            self.media_list.add_media(media)
            self.player.set_media_list(self.media_list)
            self.current_file = file_path
            return True
        except Exception as e:
            return False

    def load_playlist(self, file_paths: List[str]) -> bool:
        """Load a playlist of files."""
        if not VLC_AVAILABLE or not self.player or not self.instance:
            return False

        try:
            self.media_list = self.instance.media_list_new()
            for file_path in file_paths:
                media = self.instance.media_new(file_path)
                self.media_list.add_media(media)
            self.player.set_media_list(self.media_list)
            self.current_file = file_paths[0] if file_paths else None
            return True
        except Exception as e:
            return False

    def play(self) -> bool:
        """Start/resume playback."""
        if not VLC_AVAILABLE or not self.player:
            return False

        try:
            self.player.play()
            self.is_playing = True
            return True
        except Exception as e:
            return False

    def pause(self) -> bool:
        """Pause playback."""
        if not VLC_AVAILABLE or not self.player:
            return False

        try:
            self.player.pause()
            self.is_playing = False
            return True
        except Exception as e:
            return False

    def stop(self) -> bool:
        """Stop playback."""
        if not VLC_AVAILABLE or not self.player:
            return False

        try:
            self.player.stop()
            self.is_playing = False
            return True
        except Exception as e:
            return False

    def toggle_pause(self) -> bool:
        """Toggle between play and pause."""
        if self.is_playing:
            return self.pause()
        else:
            return self.play()

    def next(self) -> bool:
        """Skip to next song in playlist."""
        if not VLC_AVAILABLE or not self.player:
            return False

        try:
            self.player.next()
            return True
        except Exception as e:
            return False

    def previous(self) -> bool:
        """Skip to previous song in playlist."""
        if not VLC_AVAILABLE or not self.player:
            return False

        try:
            self.player.previous()
            return True
        except Exception as e:
            return False

    def set_volume(self, volume: int) -> bool:
        """Set volume (0-100)."""
        if not VLC_AVAILABLE or not self.player:
            return False

        try:
            volume = max(0, min(100, volume))
            self.player.get_media_player().audio_set_volume(volume)
            return True
        except Exception as e:
            return False

    def get_volume(self) -> int:
        """Get current volume (0-100)."""
        if not VLC_AVAILABLE or not self.player:
            return 50

        try:
            return self.player.get_media_player().audio_get_volume()
        except Exception as e:
            return 50

    def is_vlc_available(self) -> bool:
        """Check if VLC is available."""
        return VLC_AVAILABLE and self.player is not None

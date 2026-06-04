import vlc
import os
import random
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from enum import Enum
from dataclasses import dataclass
from collections import deque


class PlayerStatus(Enum):
    """Player status enumeration"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class SongItem:
    """Represents a single song"""
    name: str
    album: str
    artist: str
    path: str  # Full file path
    
    def __eq__(self, other):
        if isinstance(other, SongItem):
            return self.path == other.path
        return False
    
    def __hash__(self):
        return hash(self.path)
    
    def __repr__(self):
        return f"SongItem(artist='{self.artist}', album='{self.album}', name='{self.name}')"


class MediaPlayer:
    """
    A VLC-based media player with queue management, shuffle support, and event callbacks.
    
    Directory structure expected:
        /music_dir/artist/album/song.ext
    
    Usage:
        player = MediaPlayer(music_dir="/path/to/music")
        
        # Set up callbacks
        player.on_song_start(lambda song: print(f"Playing {song.name}"))
        player.on_song_finished(lambda: player.next())
        
        # Queue and play
        song = SongItem("Track 1", "Album", "Artist", "/path/to/song.mp3")
        player.play_song(song)
        player.pause()
        player.resume()
        player.next()
    """
    
    def __init__(self, music_dir: Optional[str] = None):
        """
        Initialize the media player.
        
        Args:
            music_dir: Optional path to music directory
        """
        self.music_dir = music_dir
        self.instance = vlc.Instance()
        self.player = self.instance.media_list_player_new()
        
        # Queue management
        self.queue: deque = deque()
        self.current_index = -1
        self.current_song: Optional[SongItem] = None
        
        # Status tracking
        self._status = PlayerStatus.STOPPED
        self._saved_volume = 50  # For mute/unmute
        
        # Event callbacks - dict of event_name -> list of callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            'song_start': [],
            'song_finished': [],
            'queue_changed': [],
            'status_changed': [],
        }
        
        # Setup media list player callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Setup VLC event callbacks for song transitions"""
        events = self.player.get_media_list().get_media().event_manager()
        # Note: We'll handle transitions via end-of-media event on the media player
        media_player = self.player.get_media_player()
        if media_player:
            event_manager = media_player.event_manager()
            event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_media_end)
            event_manager.event_attach(vlc.EventType.MediaPlayerMediaChanged, self._on_media_changed)
    
    def _on_media_end(self, event):
        """Called when a media item ends"""
        self._trigger_callbacks('song_finished')
    
    def _on_media_changed(self, event):
        """Called when media changes"""
        # Update current song based on player state
        if self.player.is_playing():
            self._update_current_song()
            self._trigger_callbacks('song_start')
    
    def _update_current_song(self):
        """Update current_song and current_index based on player state"""
        if len(self.queue) == 0:
            self.current_song = None
            self.current_index = -1
            return
        
        # The media list player handles cycling through the queue
        # We track which song is current based on the media list position
        media_list = self.player.get_media_list()
        if media_list and media_list.count() > 0:
            # Get current position - this is a bit tricky with VLC
            # We'll use the queue to track position
            for i, song in enumerate(self.queue):
                # Match against current media (simplified approach)
                # In practice, you might store a reference or use a unique ID
                pass
    
    def on_song_start(self, callback: Callable[[SongItem], None]):
        """
        Register a callback for when a song starts playing.
        
        Args:
            callback: Function to call with (song: SongItem)
        """
        self._callbacks['song_start'].append(callback)
    
    def on_song_finished(self, callback: Callable[[], None]):
        """
        Register a callback for when a song finishes.
        
        Args:
            callback: Function to call with no arguments
        """
        self._callbacks['song_finished'].append(callback)
    
    def on_queue_changed(self, callback: Callable[[List[SongItem]], None]):
        """
        Register a callback for when the queue changes.
        
        Args:
            callback: Function to call with (queue: List[SongItem])
        """
        self._callbacks['queue_changed'].append(callback)
    
    def on_status_changed(self, callback: Callable[[PlayerStatus], None]):
        """
        Register a callback for when player status changes.
        
        Args:
            callback: Function to call with (status: PlayerStatus)
        """
        self._callbacks['status_changed'].append(callback)
    
    def _trigger_callbacks(self, event_name: str, *args, **kwargs):
        """Trigger all callbacks for a given event"""
        if event_name not in self._callbacks:
            return
        for callback in self._callbacks[event_name]:
            try:
                if event_name == 'song_start' and self.current_song:
                    callback(self.current_song)
                elif event_name == 'queue_changed':
                    callback(list(self.queue))
                elif event_name == 'status_changed':
                    callback(self._status)
                else:
                    callback()
            except Exception as e:
                print(f"Error in callback {callback}: {e}")
    
    def _load_queue_to_vlc(self):
        """Load the current queue into VLC's media list"""
        media_list = self.instance.media_list_new()
        
        for song in self.queue:
            # Ensure path is absolute
            full_path = song.path if os.path.isabs(song.path) else os.path.join(self.music_dir or "", song.path)
            
            # Create media item with file:// URI
            media = self.instance.media_new(f"file://{os.path.abspath(full_path)}")
            media_list.add_media(media)
        
        self.player.set_media_list(media_list)
    
    def play_song(self, song: SongItem, shuffle: bool = False):
        """
        Clear queue and play a single song immediately.
        
        Args:
            song: SongItem to play
            shuffle: Ignored for single song (included for API consistency)
        """
        self.queue.clear()
        self.queue.append(song)
        self.current_song = song
        self.current_index = 0
        
        self._load_queue_to_vlc()
        self.player.play()
        self._set_status(PlayerStatus.PLAYING)
        self._trigger_callbacks('queue_changed')
        self._trigger_callbacks('song_start')
    
    def queue_song(self, song: SongItem):
        """
        Add a song to the end of the queue.
        
        Args:
            song: SongItem to queue
        """
        self.queue.append(song)
        self._trigger_callbacks('queue_changed')
    
    def queue_album(self, artist: str, album: str, shuffle: bool = False):
        """
        Add all songs from an album to the queue.
        
        Args:
            artist: Artist name
            album: Album name
            shuffle: Whether to shuffle the songs
        """
        songs = self._get_album_songs(artist, album)
        if shuffle:
            random.shuffle(songs)
        self.queue.extend(songs)
        self._trigger_callbacks('queue_changed')
    
    def queue_artist(self, artist: str, shuffle: bool = False):
        """
        Add all songs from an artist to the queue.
        
        Args:
            artist: Artist name
            shuffle: Whether to shuffle the songs
        """
        songs = self._get_artist_songs(artist)
        if shuffle:
            random.shuffle(songs)
        self.queue.extend(songs)
        self._trigger_callbacks('queue_changed')
    
    def queue_all_songs(self, shuffle: bool = False):
        """
        Add all songs to the queue.
        
        Args:
            shuffle: Whether to shuffle the songs
        """
        if not self.music_dir:
            raise ValueError("music_dir must be set to use queue_all_songs")
        
        songs = self._scan_all_songs()
        if shuffle:
            random.shuffle(songs)
        self.queue.extend(songs)
        self._trigger_callbacks('queue_changed')
    
    def play_album(self, artist: str, album: str, shuffle: bool = False):
        """
        Clear queue and play all songs from an album.
        
        Args:
            artist: Artist name
            album: Album name
            shuffle: Whether to shuffle the songs
        """
        self.queue.clear()
        self.queue_album(artist, album, shuffle=shuffle)
        
        if len(self.queue) > 0:
            self.current_song = self.queue[0]
            self.current_index = 0
            self._load_queue_to_vlc()
            self.player.play()
            self._set_status(PlayerStatus.PLAYING)
            self._trigger_callbacks('song_start')
    
    def play_artist(self, artist: str, shuffle: bool = False):
        """
        Clear queue and play all songs from an artist.
        
        Args:
            artist: Artist name
            shuffle: Whether to shuffle the songs
        """
        self.queue.clear()
        self.queue_artist(artist, shuffle=shuffle)
        
        if len(self.queue) > 0:
            self.current_song = self.queue[0]
            self.current_index = 0
            self._load_queue_to_vlc()
            self.player.play()
            self._set_status(PlayerStatus.PLAYING)
            self._trigger_callbacks('song_start')
    
    def play_all_songs(self, shuffle: bool = False):
        """
        Clear queue and play all songs in the library.
        
        Args:
            shuffle: Whether to shuffle the songs
        """
        self.queue.clear()
        self.queue_all_songs(shuffle=shuffle)
        
        if len(self.queue) > 0:
            self.current_song = self.queue[0]
            self.current_index = 0
            self._load_queue_to_vlc()
            self.player.play()
            self._set_status(PlayerStatus.PLAYING)
            self._trigger_callbacks('song_start')
    
    def pause(self):
        """Pause playback"""
        if self._status == PlayerStatus.PLAYING:
            self.player.pause()
            self._set_status(PlayerStatus.PAUSED)
    
    def resume(self):
        """Resume playback"""
        if self._status == PlayerStatus.PAUSED:
            self.player.play()
            self._set_status(PlayerStatus.PLAYING)
    
    def stop(self):
        """Stop playback and clear queue"""
        self.player.stop()
        self.queue.clear()
        self.current_song = None
        self.current_index = -1
        self._set_status(PlayerStatus.STOPPED)
        self._trigger_callbacks('queue_changed')
    
    def next(self):
        """Skip to next song in queue"""
        if len(self.queue) == 0:
            return
        
        self.player.next()
        self._advance_queue_position()
    
    def previous(self):
        """Skip to previous song in queue"""
        if len(self.queue) == 0:
            return
        
        self.player.previous()
        self._go_back_queue_position()
    
    def _advance_queue_position(self):
        """Advance to next song in queue"""
        self.current_index = min(self.current_index + 1, len(self.queue) - 1)
        if self.current_index >= 0 and self.current_index < len(self.queue):
            self.current_song = self.queue[self.current_index]
            self._trigger_callbacks('song_start')
    
    def _go_back_queue_position(self):
        """Go to previous song in queue"""
        self.current_index = max(self.current_index - 1, 0)
        if self.current_index >= 0 and self.current_index < len(self.queue):
            self.current_song = self.queue[self.current_index]
            self._trigger_callbacks('song_start')
    
    def remove_from_queue(self, index: int):
        """
        Remove a song from the queue by index.
        
        Args:
            index: Index of song to remove
        """
        if 0 <= index < len(self.queue):
            removed = self.queue[index]
            # Convert deque to list, remove, convert back
            queue_list = list(self.queue)
            del queue_list[index]
            self.queue = deque(queue_list)
            
            # Adjust current index if needed
            if index < self.current_index:
                self.current_index -= 1
            elif index == self.current_index and self.current_index >= len(self.queue):
                self.current_index = len(self.queue) - 1
            
            self._trigger_callbacks('queue_changed')
    
    def clear_queue(self):
        """Clear the entire queue"""
        self.queue.clear()
        self.current_index = -1
        self.current_song = None
        self._trigger_callbacks('queue_changed')
    
    def get_queue(self) -> List[SongItem]:
        """Get a copy of the current queue"""
        return list(self.queue)
    
    def get_current_song(self) -> Optional[SongItem]:
        """Get the currently playing song"""
        return self.current_song
    
    def get_status(self) -> PlayerStatus:
        """Get current player status"""
        return self._status
    
    def is_playing(self) -> bool:
        """Check if player is currently playing"""
        return self._status == PlayerStatus.PLAYING
    
    def get_current_time(self) -> int:
        """Get current playback position in milliseconds"""
        media_player = self.player.get_media_player()
        if media_player:
            return media_player.get_time()
        return 0
    
    def get_duration(self) -> int:
        """Get duration of current song in milliseconds"""
        media_player = self.player.get_media_player()
        if media_player:
            return media_player.get_length()
        return 0
    
    def seek(self, milliseconds: int):
        """
        Seek to a specific position in the current song.
        
        Args:
            milliseconds: Position to seek to
        """
        media_player = self.player.get_media_player()
        if media_player:
            media_player.set_time(milliseconds)
    
    def set_volume(self, volume: int):
        """
        Set the playback volume.
        
        Args:
            volume: Volume level from 0 (mute) to 100 (max)
        """
        volume = max(0, min(100, volume))  # Clamp to 0-100
        media_player = self.player.get_media_player()
        if media_player:
            media_player.audio_set_volume(volume)
    
    def get_volume(self) -> int:
        """
        Get the current playback volume.
        
        Returns:
            Volume level from 0 to 100
        """
        media_player = self.player.get_media_player()
        if media_player:
            return media_player.audio_get_volume()
        return 0
    
    def mute(self):
        """Mute the player (save current volume for unmute)"""
        if not hasattr(self, '_saved_volume'):
            self._saved_volume = self.get_volume()
        self.set_volume(0)
    
    def unmute(self):
        """Unmute the player (restore previous volume)"""
        if hasattr(self, '_saved_volume'):
            self.set_volume(self._saved_volume)
        else:
            self.set_volume(50)  # Default to 50% if no saved volume
    
    def is_muted(self) -> bool:
        """Check if player is muted"""
        return self.get_volume() == 0
    
    def increase_volume(self, increment: int = 5) -> int:
        """
        Increase volume by a given amount.
        
        Args:
            increment: Amount to increase (default 5%)
            
        Returns:
            New volume level
        """
        current = self.get_volume()
        new_volume = min(100, current + increment)
        self.set_volume(new_volume)
        return new_volume
    
    def decrease_volume(self, decrement: int = 5) -> int:
        """
        Decrease volume by a given amount.
        
        Args:
            decrement: Amount to decrease (default 5%)
            
        Returns:
            New volume level
        """
        current = self.get_volume()
        new_volume = max(0, current - decrement)
        self.set_volume(new_volume)
        return new_volume
    
    def _set_status(self, status: PlayerStatus):
        """Set player status and trigger callbacks"""
        if self._status != status:
            self._status = status
            self._trigger_callbacks('status_changed')
    
    # Helper methods for scanning directory structure
    
    def _get_album_songs(self, artist: str, album: str) -> List[SongItem]:
        """Get all songs in an album"""
        if not self.music_dir:
            return []
        
        album_path = os.path.join(self.music_dir, artist, album)
        songs = []
        
        if not os.path.exists(album_path):
            return songs
        
        for filename in sorted(os.listdir(album_path)):
            filepath = os.path.join(album_path, filename)
            if os.path.isfile(filepath) and self._is_audio_file(filepath):
                song = SongItem(
                    name=filename,
                    album=album,
                    artist=artist,
                    path=filepath
                )
                songs.append(song)
        
        return songs
    
    def _get_artist_songs(self, artist: str) -> List[SongItem]:
        """Get all songs by an artist"""
        if not self.music_dir:
            return []
        
        artist_path = os.path.join(self.music_dir, artist)
        songs = []
        
        if not os.path.exists(artist_path):
            return songs
        
        for album in sorted(os.listdir(artist_path)):
            album_path = os.path.join(artist_path, album)
            if os.path.isdir(album_path):
                songs.extend(self._get_album_songs(artist, album))
        
        return songs
    
    def _scan_all_songs(self) -> List[SongItem]:
        """Scan all songs in the music directory"""
        if not self.music_dir:
            return []
        
        songs = []
        
        if not os.path.exists(self.music_dir):
            return songs
        
        for artist in sorted(os.listdir(self.music_dir)):
            artist_path = os.path.join(self.music_dir, artist)
            if os.path.isdir(artist_path):
                songs.extend(self._get_artist_songs(artist))
        
        return songs
    
    @staticmethod
    def _is_audio_file(filepath: str) -> bool:
        """Check if file is an audio file"""
        audio_extensions = {
            '.mp3', '.flac', '.wav', '.m4a', '.ogg', '.opus',
            '.aac', '.wma', '.alac', '.ape', '.dsf', '.dsd'
        }
        _, ext = os.path.splitext(filepath)
        return ext.lower() in audio_extensions
    
    def __del__(self):
        """Cleanup VLC instance"""
        try:
            if hasattr(self, 'player'):
                self.player.stop()
        except:
            pass
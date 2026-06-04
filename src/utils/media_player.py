import subprocess
import time
import os
import random
import shutil
from pathlib import Path
from typing import List, Optional, Callable, Dict
from enum import Enum
from dataclasses import dataclass
from collections import deque
from threading import Thread

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
    Lightweight media player for Pi Zero using persistent ffplay via stdin.
    Supports MP3, FLAC, WAV, OGG, M4A, and other common audio formats.
    
    Optimized for Pi Zero: keeps ffplay running and feeds it audio via stdin
    for instant song switching without subprocess startup overhead.
    
    Directory structure expected:
        /music_dir/artist/album/song.ext
    """
    
    def __init__(self, music_dir: Optional[str] = None, prewarm: bool = True):
        """
        Initialize the media player.
        
        Args:
            music_dir: Optional path to music directory
            prewarm: If True, start ffplay daemon immediately (default True)
        """
        self.music_dir = music_dir
        
        # Check if ffplay is available
        self._check_ffplay_available()
        
        # Queue management
        self.queue: deque = deque()
        self.current_index = -1
        self.current_song: Optional[SongItem] = None
        
        # Playback process (persistent ffplay)
        self.process: Optional[subprocess.Popen] = None
        self._status = PlayerStatus.STOPPED
        
        # Volume (0-100)
        self._volume = 50
        self._saved_volume = 50
        
        # Event callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            'song_start': [],
            'song_finished': [],
            'queue_changed': [],
            'status_changed': [],
        }
        
        # Monitor thread for detecting song end
        self._monitor_thread: Optional[Thread] = None
        self._stop_monitor = False
        
        # Initialize persistent ffplay if requested
        if prewarm:
            self._init_ffplay_daemon()
    
    def _check_ffplay_available(self):
        if shutil.which("ffplay") is None:
            raise RuntimeError(
                "ffplay not found. Install ffmpeg:\n"
                "  sudo apt-get install ffmpeg"
            )
    
    def _init_ffplay_daemon(self):
        """
        Start persistent ffplay daemon reading from stdin.
        This is called once during init (or on demand) and stays running.
        """
        # Don't restart if already running
        if self.process and self.process.poll() is None:
            return
        
        try:
            cmd = [
                'ffplay',
                '-nodisp',                  # No video window
                '-autoexit',                # Exit when input stream ends
                '-hide_banner',             # Suppress banner
                '-loglevel', 'quiet',       # Minimal logging
                '-volume', str(self._volume),
                '-'                         # Read from stdin
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0  # Unbuffered for responsiveness
            )
            
            print(f"[ffplay] daemon initialized (PID: {self.process.pid})")
            
        except Exception as e:
            print(f"Error initializing ffplay daemon: {e}")
            self.process = None
    
    def _restart_ffplay_daemon(self):
        """Restart ffplay daemon if it has crashed"""
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=1)
        except:
            pass
        finally:
            self.process = None
        
        self._init_ffplay_daemon()
        
    def create_song_item(self, song, album, artist):
        return SongItem(song, album, artist, self.music_dir + "/" + artist + "/" + album + "/" + song)

    def on_song_start(self, callback: Callable[[SongItem], None]):
        """Register callback for when a song starts"""
        self._callbacks['song_start'].append(callback)
    
    def on_song_finished(self, callback: Callable[[], None]):
        """Register callback for when a song finishes"""
        self._callbacks['song_finished'].append(callback)
    
    def on_queue_changed(self, callback: Callable[[List[SongItem]], None]):
        """Register callback for when queue changes"""
        self._callbacks['queue_changed'].append(callback)
    
    def on_status_changed(self, callback: Callable[[PlayerStatus], None]):
        """Register callback for when status changes"""
        self._callbacks['status_changed'].append(callback)
    
    def _trigger_callbacks(self, event_name: str):
        """Trigger all callbacks for an event"""
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
                print(f"Error in callback: {e}")
    
    def _monitor_playback(self):
        """Monitor ffplay process and detect when song ends"""
        while not self._stop_monitor and self.process:
            if self.process.poll() is not None:
                # Process ended (song finished)
                if self._status == PlayerStatus.PLAYING:
                    self._trigger_callbacks('song_finished')
                    # Auto-play next if available
                    if len(self.queue) > self.current_index + 1:
                        self.next()
                    else:
                        self._set_status(PlayerStatus.STOPPED)
                break
            time.sleep(0.5)
    
    def _start_monitor(self):
        """Start monitoring thread"""
        self._stop_monitor = False
        self._monitor_thread = Thread(target=self._monitor_playback, daemon=True)
        self._monitor_thread.start()
    
    def _stop_monitor_thread(self):
        """Stop monitoring thread"""
        self._stop_monitor = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)

    def _play_file(self, file_path: str):
        """
        Stream audio file to persistent ffplay via stdin.
        
        Args:
            file_path: Full path to audio file
        """
        # Make sure file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        # Ensure ffplay daemon is running
        if not self.process or self.process.poll() is not None:
            self._init_ffplay_daemon()
        
        try:
            # Read file and stream to ffplay stdin
            with open(file_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Write to ffplay's stdin
            self.process.stdin.write(audio_data)
            self.process.stdin.flush()
            
            self._set_status(PlayerStatus.PLAYING)
            self._start_monitor()
            
        except BrokenPipeError:
            # ffplay crashed, restart and retry
            print("[ffplay] broken pipe, restarting daemon...")
            self._restart_ffplay_daemon()
            # Retry once
            try:
                with open(file_path, 'rb') as audio_file:
                    audio_data = audio_file.read()
                self.process.stdin.write(audio_data)
                self.process.stdin.flush()
                self._set_status(PlayerStatus.PLAYING)
                self._start_monitor()
            except Exception as e:
                print(f"Error retrying playback: {e}")
                self._set_status(PlayerStatus.STOPPED)
        except Exception as e:
            print(f"Error streaming file: {e}")
            self._set_status(PlayerStatus.STOPPED)
    
    def play_song(self, song: SongItem):
        """
        Clear queue and play a single song immediately.
        
        Args:
            song: SongItem to play
        """
        self.queue.clear()
        self.queue.append(song)
        self.current_song = song
        self.current_index = 0

        print(f"Playing: {song.artist} - {song.name}")

        self._trigger_callbacks('queue_changed')
        self._trigger_callbacks('song_start')
        self._play_file(song.path)
    
    def queue_song(self, song: SongItem):
        """Add a song to the queue"""
        self.queue.append(song)
        self._trigger_callbacks('queue_changed')
    
    def queue_album(self, artist: str, album: str, shuffle: bool = False):
        """Add all songs from an album to queue"""
        songs = self._get_album_songs(artist, album)
        if shuffle:
            random.shuffle(songs)
        self.queue.extend(songs)
        self._trigger_callbacks('queue_changed')
    
    def queue_artist(self, artist: str, shuffle: bool = False):
        """Add all songs by an artist to queue"""
        songs = self._get_artist_songs(artist)
        if shuffle:
            random.shuffle(songs)
        self.queue.extend(songs)
        self._trigger_callbacks('queue_changed')
    
    def queue_all_songs(self, shuffle: bool = False):
        """Add all songs in library to queue"""
        if not self.music_dir:
            raise ValueError("music_dir must be set")
        
        songs = self._scan_all_songs()
        if shuffle:
            random.shuffle(songs)
        self.queue.extend(songs)
        self._trigger_callbacks('queue_changed')
    
    def play_album(self, artist: str, album: str, shuffle: bool = False):
        """Clear queue and play all songs from album"""
        self.queue.clear()
        self.queue_album(artist, album, shuffle=shuffle)
        
        if len(self.queue) > 0:
            self.current_song = self.queue[0]
            self.current_index = 0
            self._trigger_callbacks('queue_changed')
            self._trigger_callbacks('song_start')
            self._play_file(self.queue[0].path)
    
    def play_artist(self, artist: str, shuffle: bool = False):
        """Clear queue and play all songs by artist"""
        self.queue.clear()
        self.queue_artist(artist, shuffle=shuffle)
        
        if len(self.queue) > 0:
            self.current_song = self.queue[0]
            self.current_index = 0
            self._trigger_callbacks('queue_changed')
            self._trigger_callbacks('song_start')
            self._play_file(self.queue[0].path)
    
    def play_all_songs(self, shuffle: bool = False):
        """Clear queue and play all songs in library"""
        self.queue.clear()
        self.queue_all_songs(shuffle=shuffle)
        
        if len(self.queue) > 0:
            self.current_song = self.queue[0]
            self.current_index = 0
            self._trigger_callbacks('queue_changed')
            self._trigger_callbacks('song_start')
            self._play_file(self.queue[0].path)
    
    def pause(self):
        """Pause playback"""
        if self.process and self._status == PlayerStatus.PLAYING:
            # Send space to ffplay to pause
            try:
                self.process.stdin.write(b' ')
                self.process.stdin.flush()
            except:
                pass
            self._set_status(PlayerStatus.PAUSED)
    
    def resume(self):
        """Resume playback"""
        if self.process and self._status == PlayerStatus.PAUSED:
            # Send space to ffplay to resume
            try:
                self.process.stdin.write(b' ')
                self.process.stdin.flush()
            except:
                pass
            self._set_status(PlayerStatus.PLAYING)
    
    def stop(self):
        """Stop playback and clear queue"""
        self._stop_monitor_thread()
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                try:
                    self.process.kill()
                except:
                    pass
            self.process = None
        
        self.queue.clear()
        self.current_song = None
        self.current_index = -1
        self._set_status(PlayerStatus.STOPPED)
        self._trigger_callbacks('queue_changed')
    
    def next(self):
        """Skip to next song in queue"""
        if len(self.queue) == 0:
            return
        
        self.current_index = min(self.current_index + 1, len(self.queue) - 1)
        if self.current_index < len(self.queue):
            self.current_song = self.queue[self.current_index]
            self._trigger_callbacks('song_start')
            self._play_file(self.current_song.path)
    
    def previous(self):
        """Skip to previous song in queue"""
        if len(self.queue) == 0:
            return
        
        self.current_index = max(self.current_index - 1, 0)
        if self.current_index >= 0 and self.current_index < len(self.queue):
            self.current_song = self.queue[self.current_index]
            self._trigger_callbacks('song_start')
            self._play_file(self.current_song.path)
    
    def remove_from_queue(self, index: int):
        """Remove a song from the queue"""
        if 0 <= index < len(self.queue):
            queue_list = list(self.queue)
            del queue_list[index]
            self.queue = deque(queue_list)
            
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
    
    def _set_status(self, status: PlayerStatus):
        """Set player status and trigger callbacks"""
        if self._status != status:
            self._status = status
            self._trigger_callbacks('status_changed')
    
    # Volume control
    
    def set_volume(self, volume: int):
        """
        Set volume (0-100).
        
        Args:
            volume: Volume level 0-100
        """
        self._volume = max(0, min(100, volume))
        
        # Note: ffplay doesn't support live volume change via stdin.
        # Volume changes take effect on the next song played.
        # For live volume control, would need to restart ffplay or use a different backend.
    
    def get_volume(self) -> int:
        """Get current volume"""
        return self._volume
    
    def mute(self):
        """Mute player"""
        self._saved_volume = self._volume
        self.set_volume(0)
    
    def unmute(self):
        """Unmute player"""
        self.set_volume(self._saved_volume)
    
    def is_muted(self) -> bool:
        """Check if muted"""
        return self._volume == 0
    
    def increase_volume(self, increment: int = 5) -> int:
        """Increase volume by amount"""
        new_vol = min(100, self._volume + increment)
        self.set_volume(new_vol)
        return new_vol
    
    def decrease_volume(self, decrement: int = 5) -> int:
        """Decrease volume by amount"""
        new_vol = max(0, self._volume - decrement)
        self.set_volume(new_vol)
        return new_vol
    
    # Directory scanning
    
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
        """Scan all songs in library"""
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
            '.aac', '.wma', '.alac', '.ape'
        }
        _, ext = os.path.splitext(filepath)
        return ext.lower() in audio_extensions
    
    def __del__(self):
        """Cleanup"""
        try:
            self.stop()
        except:
            pass
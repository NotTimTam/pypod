import json
from pathlib import Path
from typing import Dict, List, Any
import os

from ..models.song import Song
from ..models.album import Album
from ..models.artist import Artist
from ..utils.constants import AUDIO_EXTENSIONS
from ..utils.metadata import extract_metadata
from ..utils.image_handler import get_folder_image


class CacheManager:
    def __init__(self, library_path: str, cache_file: str = "cache.json"):
        self.library_path = Path(library_path)
        self.cache_file = Path(cache_file)
        self.cache_data: Dict[str, Any] = {"songs": [], "artists": [], "albums": []}

    def load_or_build(self) -> tuple:
        """Load cache if valid, otherwise rebuild from library."""
        if self.cache_file.exists():
            if self._cache_is_valid():
                return self._load_cache()

        # Rebuild cache
        return self._build_cache()

    def _cache_is_valid(self) -> bool:
        """Check if cache exists and is newer than library files."""
        if not self.cache_file.exists():
            return False

        try:
            cache_mtime = self.cache_file.stat().st_mtime
            library_mtime = self.library_path.stat().st_mtime

            # Also check if library has been modified recursively
            for _ in self.library_path.rglob("*"):
                if _.is_file() and _.stat().st_mtime > cache_mtime:
                    return False
            return cache_mtime > library_mtime
        except:
            return False

    def _load_cache(self) -> tuple:
        """Load cache.json and convert to objects."""
        try:
            with open(self.cache_file, "r") as f:
                data = json.load(f)

            songs = [
                Song(
                    filename=s["filename"],
                    path=s["path"],
                    artist=s["artist"],
                    album=s["album"],
                    duration=s.get("duration"),
                    track_num=s.get("track_num"),
                    title = s.get("title") or s['filename'],
                )
                for s in data.get("songs", [])
            ]

            albums = [
                Album(
                    name=a["name"],
                    artist=a["artist"],
                    path=a["path"],
                    song_ids=a.get("song_ids", []),
                )
                for a in data.get("albums", [])
            ]

            artists = [
                Artist(
                    name=a["name"],
                    path=a["path"],
                    song_ids=a.get("song_ids", []),
                    album_ids=a.get("album_ids", []),
                )
                for a in data.get("artists", [])
            ]

            return songs, albums, artists
        except Exception as e:
            return [], [], []

    def _build_cache(self) -> tuple:
        """Scan library and build cache."""
        songs: List[Song] = []
        albums: List[Album] = []
        artists: Dict[str, Artist] = {}
        album_map: Dict[tuple, Album] = {}  # (artist, album_name) -> Album

        song_id = 0

        # Scan: /LIBRARY/ARTIST/ALBUM/SONG
        if not self.library_path.exists():
            self._save_cache([], [], [])
            return [], [], []

        for artist_dir in sorted(self.library_path.iterdir()):
            if not artist_dir.is_dir():
                continue

            artist_name = artist_dir.name
            if artist_name not in artists:
                artists[artist_name] = Artist(
                    name=artist_name,
                    path=str(artist_dir),
                    song_ids=[],
                    album_ids=[],
                )

            for album_dir in sorted(artist_dir.iterdir()):
                if not album_dir.is_dir():
                    continue

                album_name = album_dir.name
                album_key = (artist_name, album_name)

                if album_key not in album_map:
                    album = Album(
                        name=album_name,
                        artist=artist_name,
                        path=str(album_dir),
                        song_ids=[],
                    )
                    album_map[album_key] = album
                    album_id = len(albums)
                    albums.append(album)
                    artists[artist_name].album_ids.append(album_id)
                else:
                    album = album_map[album_key]

                # Scan for audio files
                for file_path in sorted(album_dir.iterdir()):
                    if file_path.is_file() and file_path.suffix.lower() in AUDIO_EXTENSIONS:
                        # Load metadata for songs
                        metadata = extract_metadata(file_path.stem)

                        song = Song(
                            filename=metadata.get("title") or file_path.stem,
                            duration = metadata.get("duration"),
                            path=str(file_path),
                            artist=artist_name,
                            album=album_name,
                        )
                        songs.append(song)
                        album.song_ids.append(song_id)
                        artists[artist_name].song_ids.append(song_id)
                        song_id += 1

        artist_list = list(artists.values())
        self._save_cache(songs, albums, artist_list)
        return songs, albums, artist_list

    def _save_cache(self, songs: List[Song], albums: List[Album], artists: List[Artist]) -> None:
        """Save cache to cache.json."""
        try:
            data = {
                "songs": [
                    {
                        "filename": s.filename,
                        "path": s.path,
                        "artist": s.artist,
                        "album": s.album,
                        "title": s.title,
                        "duration": s.duration,
                        "track_num": s.track_num,
                    }
                    for s in songs
                ],
                "albums": [
                    {
                        "name": a.name,
                        "artist": a.artist,
                        "path": a.path,
                        "song_ids": a.song_ids,
                    }
                    for a in albums
                ],
                "artists": [
                    {
                        "name": a.name,
                        "path": a.path,
                        "song_ids": a.song_ids,
                        "album_ids": a.album_ids,
                    }
                    for a in artists
                ],
            }

            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            pass

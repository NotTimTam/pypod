import re
import json
from pathlib import Path
from urllib.parse import quote

import requests


class JellyfinError(Exception):
    pass


class Jellyfin:
    def __init__(self, url, api_key, library, download_root=None):
        """
        Initialize Jellyfin client.
        
        Args:
            url: Jellyfin server URL (e.g., "http://localhost:8096")
            api_key: API key for authentication
            library: Library name (plaintext) or library ID
            download_root: Optional root directory for downloads
        """
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.library = library
        self.download_root = Path(download_root) if download_root is not None else None
        self.session = requests.Session()
        self.session.headers.update({
            "X-Emby-Token": self.api_key,
            "Accept": "application/json",
            "User-Agent": "pipod-jellyfin-client/1.0",
        })
        self._section_id = None
        self._user_id = None

    def _build_url(self, path):
        return f"{self.url}/{path.lstrip('/')}"

    def _request(self, path, params=None, stream=False):
        url = self._build_url(path)
        resp = self.session.get(url, params=params, stream=stream, timeout=30)
        if resp.status_code >= 400:
            raise JellyfinError(f"Jellyfin request failed ({resp.status_code}): {resp.text}")
        return resp if stream else resp.json()

    def _get_user_id(self):
        """Get the current user ID from /Users/Me endpoint."""
        if self._user_id:
            return self._user_id
        
        user_info = self._request("Users/Me")
        self._user_id = user_info.get("Id")
        if not self._user_id:
            raise JellyfinError("Could not determine user ID from /Users/Me endpoint")
        return self._user_id

    def _resolve_library_section(self):
        """
        Resolve library name or ID to actual library ID.
        
        Uses: GET /Users/{userId}/Views
        """
        if self._section_id:
            return self._section_id

        user_id = self._get_user_id()
        response = self._request(f"Users/{user_id}/Views")
        
        views = response.get("Items", []) if isinstance(response, dict) else response
        
        if not views:
            raise JellyfinError(
                f"No library views found for user {user_id}. "
                "Check your Jellyfin server and user permissions."
            )

        for view in views:
            view_id = view.get("Id")
            view_name = view.get("Name", "")
            
            if view_id == self.library:
                self._section_id = view_id
                return self._section_id
            
            if isinstance(self.library, str) and view_name.lower() == self.library.lower():
                self._section_id = view_id
                return self._section_id

        available = [f"{v.get('Name')} (ID: {v.get('Id')}, Type: {v.get('Type')})" for v in views]
        raise JellyfinError(
            f"Unable to resolve library '{self.library}'.\n"
            f"Available libraries:\n" + "\n".join(f"  - {lib}" for lib in available)
        )

    @staticmethod
    def _sanitize_path_component(value):
        value = str(value).strip()
        value = re.sub(r'[<>:"/\\|?*]+', "_", value)
        value = re.sub(r"\s+", " ", value)
        return value or "Unknown"

    def _ensure_download_root(self):
        if self.download_root is None:
            raise JellyfinError("No download_root configured for Jellyfin client.")
        self.download_root.mkdir(parents=True, exist_ok=True)
        return self.download_root

    def get_artists(self):
        """
        Get all music artists from the music library.
        
        CRITICAL FIX from original code:
        - Original used: /Users/{userId}/Items with IncludeItemTypes=MusicArtist (400 Bad Request)
        - Correct endpoint: /Artists (dedicated artists endpoint)
        
        This is the proper way to get artists per Jellyfin API.
        Reference: Issue #16284 shows /Artists endpoint usage
        """
        params = {
            "Limit": 1000,
        }
        data = self._request("Artists", params=params)
        items = data.get("Items", []) if isinstance(data, dict) else data
        return [
            {
                "Id": item.get("Id"),
                "Name": item.get("Name"),
                "Genres": item.get("Genres", []),
                "AlbumCount": item.get("AlbumCount", 0),
            }
            for item in items
        ]

    def get_albums(self, artist_id=None):
        """
        Get all music albums, optionally filtered by artist.
        
        CRITICAL FIX:
        - Original used: /Users/{userId}/Items with IncludeItemTypes=MusicAlbum (questionable)
        - Better endpoint: /Artists/{artistId}/Albums or /Albums
        
        Note: The /Items endpoint approach may still cause issues.
        Using library-aware /Albums endpoint is safer.
        """
        user_id = self._get_user_id()
        section_id = self._resolve_library_section()
        
        if artist_id:
            # Get albums for a specific artist
            params = {"Limit": 1000}
            data = self._request(f"Artists/{quote(artist_id)}/Albums", params=params)
        else:
            # Get all albums - using Items endpoint with proper parameters
            params = {
                "Recursive": "true",
                "IncludeItemTypes": "MusicAlbum",
                "ParentId": section_id,
                "Limit": 1000,
            }
            data = self._request(f"Users/{user_id}/Items", params=params)
        
        items = data.get("Items", []) if isinstance(data, dict) else data
        return [
            {
                "Id": item.get("Id"),
                "Name": item.get("Name"),
                "Artists": item.get("Artists", []),
                "AlbumArtists": item.get("AlbumArtists", []),
                "Genres": item.get("Genres", []),
                "AlbumCount": item.get("AlbumCount", 0),
            }
            for item in items
        ]

    def get_genres(self):
        """
        Get all music genres from the configured library.
        
        Uses: GET /Genres
        """
        section_id = self._resolve_library_section()
        params = {
            "IncludeItemTypes": "Audio",
            "ParentId": section_id,
            "Recursive": "true",
        }
        genres = self._request("Genres", params=params)
        if isinstance(genres, dict):
            genres = genres.get("Items", [])
        return [
            {"Id": genre.get("Id"), "Name": genre.get("Name")}
            for genre in genres
        ]

    def get_playlists(self):
        """
        Get all playlists for the current user.
        
        Uses: GET /Users/{userId}/Playlists
        """
        user_id = self._get_user_id()
        params = {
            "Recursive": "true",
            "IncludeItemTypes": "Audio",
            "Fields": "ItemCount,Name,IsLocked,UserId",
            "Limit": 1000,
        }
        playlists = self._request(f"Users/{user_id}/Playlists", params=params)
        if isinstance(playlists, dict):
            playlists = playlists.get("Items", [])
        return [
            {
                "Id": playlist.get("Id"),
                "Name": playlist.get("Name"),
                "ItemCount": playlist.get("ItemCount", 0),
                "IsLocked": playlist.get("IsLocked", False),
            }
            for playlist in playlists
        ]

    def get_playlist_items(self, playlist_id):
        """
        Get all items in a specific playlist.
        
        Uses: GET /Playlists/{playlistId}/Items
        """
        params = {
            "Fields": "Album,AlbumId,Artists,AlbumArtists,Genres,Path,MediaSources",
            "Limit": 1000,
        }
        playlist_items = self._request(f"Playlists/{quote(playlist_id)}/Items", params=params)
        if isinstance(playlist_items, dict):
            playlist_items = playlist_items.get("Items", [])
        return [
            {
                "Id": item.get("Id"),
                "Name": item.get("Name"),
                "Album": item.get("Album"),
                "AlbumId": item.get("AlbumId"),
                "Artists": item.get("Artists", []),
                "AlbumArtists": item.get("AlbumArtists", []),
                "Genres": item.get("Genres", []),
                "Path": item.get("Path"),
            }
            for item in playlist_items
        ]

    def download_playlist(self, playlist_id, download_root=None):
        """Download all songs in a playlist."""
        download_root = Path(download_root) if download_root is not None else self.download_root
        if download_root is None:
            raise JellyfinError("download_playlist requires a download_root or Jellyfin(download_root=...) to be configured.")

        download_root.mkdir(parents=True, exist_ok=True)
        playlist_root = download_root / "playlists"
        playlist_root.mkdir(parents=True, exist_ok=True)

        playlist = self._request(f"Playlists/{quote(playlist_id)}", params={"Fields": "Name,ItemCount"})
        playlist_name = playlist.get("Name") or playlist_id
        playlist_items = self.get_playlist_items(playlist_id)

        downloaded_items = []
        for item in playlist_items:
            result = self.download_song(item["Id"], download_root=download_root)
            downloaded_items.append({
                "Id": item["Id"],
                "Name": item["Name"],
                "Artist": result["artist"],
                "Album": result["album"],
                "Path": result["path"],
                "AlbumArt": result["album_art"],
            })

        playlist_file = playlist_root / f"{self._sanitize_path_component(playlist_name)}.json"
        with open(playlist_file, "w", encoding="utf-8") as out_file:
            json.dump(
                {
                    "Id": playlist_id,
                    "Name": playlist_name,
                    "ItemCount": playlist.get("ItemCount", len(downloaded_items)),
                    "Items": downloaded_items,
                },
                out_file,
                indent=2,
                ensure_ascii=False,
            )

        return {
            "playlist_id": playlist_id,
            "name": playlist_name,
            "playlist_file": str(playlist_file),
            "items": downloaded_items,
        }

    def get_songs(self, album_id=None, artist_id=None, genre_id=None):
        """
        Get all songs, optionally filtered by album, artist, or genre.
        
        Uses: GET /Users/{userId}/Items with IncludeItemTypes=Audio
        Note: Audio is the correct type name for songs (not MusicTrack or Song)
        """
        user_id = self._get_user_id()
        section_id = self._resolve_library_section()
        params = {
            "Recursive": "true",
            "IncludeItemTypes": "Audio",
            "ParentId": section_id,
            "Fields": "Album,AlbumId,Artists,AlbumArtists,Genres,Path,MediaSources,Duration",
            "Limit": 1000,
        }
        if album_id:
            params["AlbumIds"] = album_id
        if artist_id:
            params["ArtistIds"] = artist_id
        if genre_id:
            params["GenreIds"] = genre_id
        
        data = self._request(f"Users/{user_id}/Items", params=params)
        items = data.get("Items", []) if isinstance(data, dict) else data
        return [
            {
                "Id": item.get("Id"),
                "Name": item.get("Name"),
                "Album": item.get("Album"),
                "AlbumId": item.get("AlbumId"),
                "Artists": item.get("Artists", []),
                "AlbumArtists": item.get("AlbumArtists", []),
                "Genres": item.get("Genres", []),
                "Path": item.get("Path"),
                "Duration": item.get("Duration", 0),
            }
            for item in items
        ]

    def get_item(self, item_id, fields=None):
        """Get metadata for a specific item."""
        params = {}
        if fields:
            params["Fields"] = ",".join(fields)
        return self._request(f"Items/{quote(item_id)}", params=params)

    def _download_stream(self, path, dest_path):
        with self.session.get(self._build_url(path), stream=True, timeout=60) as resp:
            if resp.status_code >= 400:
                raise JellyfinError(
                    f"Failed downloading item stream ({resp.status_code}): {resp.text}"
                )
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as out_file:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        out_file.write(chunk)
        return dest_path

    def _album_art_path(self, album_folder):
        return album_folder / "folder.jpg"

    def _download_album_art(self, album_id, album_folder):
        art_path = self._album_art_path(album_folder)
        if art_path.exists():
            return art_path

        try:
            self._download_stream(f"Items/{quote(album_id)}/Images/Primary", art_path)
        except JellyfinError:
            return None
        return art_path

    def download_song(self, item_id, download_root=None):
        download_root = Path(download_root) if download_root is not None else self.download_root
        if download_root is None:
            raise JellyfinError("download_song requires a download_root or Jellyfin(download_root=...) to be configured.")

        download_root.mkdir(parents=True, exist_ok=True)
        item = self.get_item(item_id, fields=["Album", "AlbumId", "Artists", "AlbumArtists", "Path", "MediaSources"])

        album = self._sanitize_path_component(item.get("Album") or "Unknown Album")
        artists = item.get("Artists") or item.get("AlbumArtists") or ["Unknown Artist"]
        artist = self._sanitize_path_component(artists[0])

        album_folder = download_root / artist / album
        album_folder.mkdir(parents=True, exist_ok=True)

        filename = None
        media_sources = item.get("MediaSources") or []
        if media_sources and isinstance(media_sources, list):
            container = media_sources[0].get("Container")
            if container:
                filename = f"{self._sanitize_path_component(item.get('Name') or item_id)}.{container.lower()}"

        if not filename:
            filename = f"{self._sanitize_path_component(item.get('Name') or item_id)}.mp3"

        target_path = album_folder / filename
        download_path = f"Items/{quote(item_id)}/Download?Static=true"
        self._download_stream(download_path, target_path)

        album_id = item.get("AlbumId")
        if album_id:
            self._download_album_art(album_id, album_folder)
        else:
            try:
                self._download_stream(f"Items/{quote(item_id)}/Images/Primary", self._album_art_path(album_folder))
            except JellyfinError:
                pass

        return {
            "artist": artist,
            "album": album,
            "song": target_path.name,
            "path": str(target_path),
            "album_art": str(self._album_art_path(album_folder)) if self._album_art_path(album_folder).exists() else None,
        }

    def download_songs(self, item_ids, download_root=None):
        results = []
        for item_id in item_ids:
            results.append(self.download_song(item_id, download_root=download_root))
        return results
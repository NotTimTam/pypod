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

    def _album_art_path(self, album_folder):
        return album_folder / "folder.jpg"

    def get_artists(self):
        """
        Get all music artists from the music library.
        
        Uses: GET /Artists (dedicated artists endpoint)
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
        
        Uses: GET /Items with ArtistIds filter
        """
        params = {
            "Recursive": "true",
            "IncludeItemTypes": "MusicAlbum",
            "Limit": 1000,
        }
        
        if artist_id:
            params["ArtistIds"] = artist_id
        
        data = self._request("Items", params=params)
        
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

    def get_songs(self, album_id=None, artist_id=None, genre_id=None):
        """
        Get all songs, optionally filtered by album, artist, or genre.
        """
        params = {
            "Recursive": "true",
            "IncludeItemTypes": "Audio",
            "Fields": "Album,AlbumId,Artists,AlbumArtists,Genres,Path,MediaSources,Duration",
            "Limit": 1000,
        }
        if album_id:
            params["AlbumIds"] = album_id
        if artist_id:
            params["ArtistIds"] = artist_id
        if genre_id:
            params["GenreIds"] = genre_id
        
        data = self._request("Items", params=params)
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

    def get_item_stream(self, item_id):
        """Get a streaming response for downloading an item."""
        resp = self._request(f"Items/{quote(item_id)}/Download?Static=true", stream=True)
        if resp.status_code >= 400:
            raise JellyfinError(f"Failed to get download stream ({resp.status_code})")
        return resp

    def download_album_art(self, album_id, dest_path):
        """Download album art for an album. Returns True if successful."""
        try:
            resp = self._request(f"Items/{quote(album_id)}/Images/Primary", stream=True)
            if resp.status_code >= 400:
                return False
            
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception:
            return False
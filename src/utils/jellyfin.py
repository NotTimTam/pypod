import re
from pathlib import Path
from urllib.parse import quote
import requests

class JellyfinError(Exception):
    pass


class Jellyfin:
    def __init__(self, url, username=None, password=None, library=None, download_root=None):
        """
        Initialize Jellyfin client.
        
        Args:
            url: Jellyfin server URL (e.g., "http://192.168.1.100:8096")
            api_key: API key (legacy)
            username: Username for authentication (recommended)
            password: Password for authentication (recommended)
            library: Library name or ID
            download_root: Root folder for downloads
        """
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.library = library
        self.download_root = Path(download_root) if download_root is not None else None

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "pipod-jellyfin-client/1.0",
        })

        self._section_id = None
        self._user_id = None
        self._access_token = None

        # Perform authentication
        self._authenticate()

    def _authenticate(self):
        """Authenticate with username and password"""
        try:
            auth_url = self._build_url("Users/AuthenticateByName")
            
            payload = {
                "Username": self.username,
                "Pw": self.password
            }

            headers = {
                "Content-Type": "application/json",
                "X-Emby-Authorization": (
                    'MediaBrowser Client="pipod-jellyfin-client", '
                    'Device="PiPod", DeviceId="pipod-001", Version="1.0"'
                )
            }

            resp = requests.post(auth_url, json=payload, headers=headers, timeout=15)

            if resp.status_code != 200:
                raise JellyfinError(f"Authentication failed: {resp.status_code} - {resp.text}")

            data = resp.json()
            self._access_token = data.get("AccessToken")
            self._user_id = data.get("User", {}).get("Id")

            if not self._access_token or not self._user_id:
                raise JellyfinError("Failed to retrieve access token or user ID")

            # Use proper Authorization header (best practice)
            self.session.headers["Authorization"] = (
                f'MediaBrowser Token="{self._access_token}", '
                'Client="pipod-jellyfin-client", Device="PiPod", '
                'DeviceId="pipod-001", Version="1.0"'
            )

            print(f"Successfully authenticated as '{self.username}' (User ID: {self._user_id})")

        except Exception as e:
            raise JellyfinError(f"Authentication error: {e}")

    def _build_url(self, path):
        return f"{self.url}/{path.lstrip('/')}"

    def _request(self, path, params=None, stream=False):
        """Make request with automatic userId injection."""
        if params is None:
            params = {}

        # Always include userId when available (fixes your Guid can't be empty error)
        if self._user_id:
            params["userId"] = self._user_id

        url = self._build_url(path)
        resp = self.session.get(url, params=params, stream=stream, timeout=30)

        if resp.status_code >= 400:
            raise JellyfinError(f"Jellyfin request failed ({resp.status_code}): {resp.text}")

        return resp if stream else resp.json()

    def _get_user_id(self):
        """Get user ID (fallback if needed)."""
        if self._user_id:
            return self._user_id
        user_info = self._request("Users/Me")
        self._user_id = user_info.get("Id")
        if not self._user_id:
            raise JellyfinError("Could not determine user ID")
        return self._user_id

    def _resolve_library_section(self):
        if self._section_id:
            return self._section_id

        user_id = self._get_user_id()
        response = self._request(f"Users/{user_id}/Views")
        
        views = response.get("Items", []) if isinstance(response, dict) else response

        if not views:
            raise JellyfinError(f"No library views found for user {user_id}.")

        for view in views:
            view_id = view.get("Id")
            view_name = view.get("Name", "")

            if view_id == self.library or (isinstance(self.library, str) and view_name.lower() == self.library.lower()):
                self._section_id = view_id
                return self._section_id

        available = [f"{v.get('Name')} (ID: {v.get('Id')})" for v in views]
        raise JellyfinError(f"Library '{self.library}' not found.\nAvailable: {available}")

    # ====================== Rest of your methods (cleaned slightly) ======================

    @staticmethod
    def _sanitize_path_component(value):
        value = str(value).strip()
        value = re.sub(r'[<>:"/\\|?*]+', "_", value)
        value = re.sub(r"\s+", " ", value)
        return value or "Unknown"

    def _ensure_download_root(self):
        if self.download_root is None:
            raise JellyfinError("No download_root configured.")
        self.download_root.mkdir(parents=True, exist_ok=True)
        return self.download_root

    def get_artists(self):
        data = self._request("Artists", params={"Limit": 1000})
        items = data.get("Items", []) if isinstance(data, dict) else data
        return [{k: item.get(k) for k in ("Id", "Name", "Genres", "AlbumCount")} for item in items]

    def get_albums(self, artist_id=None):
        params = {
            "Recursive": "true",
            "IncludeItemTypes": "MusicAlbum",
            "Limit": 1000,
        }
        if artist_id:
            params["ArtistIds"] = artist_id

        data = self._request("Items", params=params)
        items = data.get("Items", []) if isinstance(data, dict) else data
        return [item for item in items]  # You can filter fields if needed

    def get_songs(self, album_id=None, artist_id=None, genre_id=None):
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
        return items

    def get_item(self, item_id, fields=None):
        params = {}
        if fields:
            params["Fields"] = ",".join(fields)
        return self._request(f"Items/{quote(item_id)}", params=params)

    # Download methods remain mostly the same (they'll benefit from userId fix)
    def _download_stream(self, path, dest_path):
        with self.session.get(self._build_url(path), stream=True, timeout=60) as resp:
            if resp.status_code >= 400:
                raise JellyfinError(f"Download failed ({resp.status_code}): {resp.text}")
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return dest_path

    # ... (keep your _album_art_path, _download_album_art, download_song, download_songs unchanged)
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
        # Your existing method (unchanged except it now benefits from better auth)
        download_root = Path(download_root) if download_root is not None else self.download_root
        if download_root is None:
            raise JellyfinError("download_song requires a download_root.")

        download_root.mkdir(parents=True, exist_ok=True)

        item = self.get_item(item_id, fields=["Album", "AlbumId", "Artists", "AlbumArtists", "Path", "MediaSources"])

        album = self._sanitize_path_component(item.get("Album") or "Unknown Album")
        artists = item.get("Artists") or item.get("AlbumArtists") or ["Unknown Artist"]
        artist = self._sanitize_path_component(artists[0])

        album_folder = download_root / artist / album
        album_folder.mkdir(parents=True, exist_ok=True)

        # Filename logic
        media_sources = item.get("MediaSources") or []
        container = media_sources[0].get("Container") if media_sources else None
        filename = f"{self._sanitize_path_component(item.get('Name') or item_id)}.{(container or 'mp3').lower()}"

        target_path = album_folder / filename
        self._download_stream(f"Items/{quote(item_id)}/Download?Static=true", target_path)

        # Album art
        album_id = item.get("AlbumId")
        if album_id:
            self._download_album_art(album_id, album_folder)

        return {
            "artist": artist,
            "album": album,
            "song": target_path.name,
            "path": str(target_path),
            "album_art": str(self._album_art_path(album_folder)) if self._album_art_path(album_folder).exists() else None,
        }

    def download_songs(self, item_ids, download_root=None):
        return [self.download_song(i, download_root) for i in item_ids]
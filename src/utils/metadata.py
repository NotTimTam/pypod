from pathlib import Path
from typing import Optional, Dict, Any
import io

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


def extract_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from audio file, returns dict with title, artist, album, duration."""
    if not MUTAGEN_AVAILABLE:
        return {"title": None, "artist": None, "album": None, "duration": None}

    result = {
        "title": None,
        "artist": None,
        "album": None,
        "duration": None,
    }

    try:
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".mp3":
            try:
                audio = EasyID3(file_path)
                result["title"] = audio.get("title", [None])[0]
                result["artist"] = audio.get("artist", [None])[0]
                result["album"] = audio.get("album", [None])[0]
            except:
                pass

        elif ext in {".flac"}:
            try:
                audio = FLAC(file_path)
                result["title"] = audio.get("title", [None])[0]
                result["artist"] = audio.get("artist", [None])[0]
                result["album"] = audio.get("album", [None])[0]
            except:
                pass

        elif ext in {".ogg", ".opus"}:
            try:
                audio = OggVorbis(file_path)
                result["title"] = audio.get("title", [None])[0]
                result["artist"] = audio.get("artist", [None])[0]
                result["album"] = audio.get("album", [None])[0]
            except:
                pass

        # Try to get duration from mutagen
        try:
            audio = None
            if ext == ".mp3":
                from mutagen.mp3 import MP3
                audio = MP3(file_path)
            elif ext == ".flac":
                audio = FLAC(file_path)
            elif ext in {".ogg", ".opus"}:
                audio = OggVorbis(file_path)

            if audio and audio.info:
                result["duration"] = int(audio.info.length)
        except:
            pass

    except Exception as e:
        pass

    return result


def get_image_from_bytes(image_bytes: bytes) -> Optional[bytes]:
    """Validate and return image bytes."""
    if image_bytes and len(image_bytes) > 0:
        return image_bytes
    return None

from dataclasses import dataclass
from typing import Optional


@dataclass
class Song:
    filename: str
    path: str
    artist: str
    album: str
    title: Optional[str] = None
    duration: Optional[int] = None
    track_num: Optional[int] = None

    def display_name(self, include_artist: bool = True) -> str:
        name = self.title or self.filename
        if include_artist:
            return f"{name} — {self.artist}"
        return name

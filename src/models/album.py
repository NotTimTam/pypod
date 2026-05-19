from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Album:
    name: str
    artist: str
    path: str
    song_ids: List[int] = field(default_factory=list)
    image_data: Optional[bytes] = None

    def display_name(self, include_artist: bool = True) -> str:
        if include_artist:
            return f"{self.name} — {self.artist}"
        return self.name

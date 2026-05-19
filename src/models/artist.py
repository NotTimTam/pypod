from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Artist:
    name: str
    path: str
    song_ids: List[int] = field(default_factory=list)
    album_ids: List[int] = field(default_factory=list)
    image_data: Optional[bytes] = None

    def display_name(self) -> str:
        return self.name

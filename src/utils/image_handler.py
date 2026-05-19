import io
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import pygame
from .constants import IMAGE_EXTENSIONS, IMAGE_PRIORITY


def load_image_from_bytes(image_bytes: bytes, max_size: int = 240) -> Optional[pygame.Surface]:
    """Convert image bytes to pygame surface, scaled to max_size."""
    if not PIL_AVAILABLE or not image_bytes:
        return None

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")

        # Scale to max_size maintaining aspect ratio
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Convert to pygame surface
        mode = img.mode
        size = img.size
        data = img.tobytes()
        return pygame.image.fromstring(data, size, mode)
    except Exception as e:
        return None


def get_folder_image(folder_path: str) -> Optional[bytes]:
    """Get image from folder, preferring square aspect ratio."""
    if not PIL_AVAILABLE:
        return None

    try:
        folder = Path(folder_path)
        images = sorted(folder.glob("*"))
        images = [f for f in images if f.suffix.lower() in IMAGE_EXTENSIONS]

        best_image = None
        best_ratio_diff = float('inf')

        for img_path in images:
            try:
                # Check filename priority first
                filename_lower = img_path.stem.lower()
                for priority_name in IMAGE_PRIORITY:
                    if priority_name in filename_lower:
                        return img_path.read_bytes()

                # Check aspect ratio (prefer 1:1)
                img = Image.open(img_path)
                width, height = img.size
                if width > 0 and height > 0:
                    ratio = min(width, height) / max(width, height)
                    ratio_diff = abs(ratio - 1.0)
                    if ratio_diff < best_ratio_diff:
                        best_ratio_diff = ratio_diff
                        best_image = img_path
            except:
                continue

        if best_image:
            return best_image.read_bytes()

        # Fallback: first image
        if images:
            return images[0].read_bytes()

    except Exception as e:
        pass

    return None


def stretch_image_to_screen(surface: Optional[pygame.Surface], width: int, height: int) -> Optional[pygame.Surface]:
    """Stretch image to fill screen dimensions."""
    if surface is None:
        return None
    return pygame.transform.scale(surface, (width, height))

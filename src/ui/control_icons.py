from PIL import Image, ImageOps
from pathlib import Path
from src.utils.constants import SCREEN_SIZE

ICON_SIZE = 24

class ControlIcons:
    """Displays optional control icons at four fixed screen positions."""

    def __init__(self, icons=None):
        """
        Initialize control icons.

        Args:
            icons: Dict mapping positions to icon filenames.
                Positions: 'a' (left, 1/4), 'b' (left, 3/4), 'x' (right, 1/4), 'y' (right, 3/4)
                Example: {"a": "chevron-up.png", "x": "chevron-down.png"}
        """
        self.icons = icons or {}
        self._image_cache = {}
        self.margin = 4

    def _load_image(self, filename):
        """Load and cache PNG image from assets/images."""
        if filename in self._image_cache:
            return self._image_cache[filename]

        path = Path(__file__).parent.parent / "assets" / "images" / filename
        try:
            img = Image.open(path).convert("RGBA").resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)
            # Invert only non-transparent pixels
            data = img.getdata()
            inverted = []
            for item in data:
                if item[3] > 0:  # If not transparent
                    inverted.append((255 - item[0], 255 - item[1], 255 - item[2], item[3]))
                else:
                    inverted.append(item)
            img.putdata(inverted)
            self._image_cache[filename] = img
            return img
        except Exception as e:
            print(f"Failed to load icon {filename}: {e}")
            return None

    def _get_position(self, position_key):
        """Calculate pixel coordinates for a position key."""
        quarter_height = SCREEN_SIZE // 5

        if position_key == "a":
            return (self.margin, quarter_height)
        elif position_key == "b":
            return (self.margin, quarter_height * 3)
        elif position_key == "x":
            return (SCREEN_SIZE - self.margin - ICON_SIZE, quarter_height)
        elif position_key == "y":
            return (SCREEN_SIZE - self.margin - ICON_SIZE, quarter_height * 3)
        return None

    def render(self, img, draw):
        """Render all configured icons."""
        for position_key, filename in self.icons.items():
            icon = self._load_image(filename)
            if icon:
                pos = self._get_position(position_key)
                if pos:
                    img.paste(icon, pos, icon)

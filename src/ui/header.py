from src.utils.constants import SCREEN_SIZE

class Header:
    """Manages menu options, navigation, and rendering."""

    def __init__(self, title="Home"):
        self.title = title

    def get_height(self, draw, font):
        bbox = draw.textbbox((0, 0), self.title, font=font)
        return bbox[3] - bbox[1]

    def render(self, img, draw, font):

        # Calculate item height
        bbox = draw.textbbox((0, 0), self.title, font=font)
        line_height = bbox[3] - bbox[1]
        padding = 4
        line_height += padding

        draw.text((int((SCREEN_SIZE / 2) - (bbox[2] / 2)), 0), self.title, fill=(255, 255, 255), font=font)

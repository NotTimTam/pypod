import time

from functools import partial
from pathlib import Path

from src.utils.screen import Screen
from src.utils.input import input_handler
from src.utils.constants import SCREEN_SIZE

from src.ui.control_icons import ControlIcons


class NowPlayingScreen(Screen):
    """Now playing screen with navigation menu."""

    def __init__(self, state=None, request_screen=None, music_dir=None, media_player=None):
        super().__init__(
            padding_top=12,
            padding_bottom=12,
            padding_left=32,
            padding_right=32
        )
        self._request_screen = request_screen
        self._music_dir = Path(music_dir) if music_dir is not None else None
        self._media_player = media_player

        self.title_offsets = [0, 0, 0]
        self.last_title_shift_times = [0, 0, 0]
        self.title_shift_interval = 0.2

        self.controls = ControlIcons(icons={
            "x": "skip-back.png",
            "y": "skip-forward.png",
            "a": "play.png",
            "b": "chevron-left.png",
        })
        self._setup_screen()

    def nullish(self):
        print(".")

    def _setup_screen(self):
        """Define screen items and their callbacks."""

    def handle_input(self):
        """Handle input."""        
        input_handler.handle_button("B", partial(self._request_screen, "home"))

    def _truncate_text(self, text, max_width, draw, font, ellipsis="..."):
        """
        Truncate text to fit within max_width, adding ellipsis if needed.
        
        Args:
            text: Text to truncate
            max_width: Maximum width in pixels
            draw: PIL ImageDraw object
            font: PIL ImageFont
            ellipsis: String to append if truncated
            
        Returns:
            Truncated text that fits within max_width
        """
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            return text
        
        # Calculate how much space ellipsis takes
        ellipsis_bbox = draw.textbbox((0, 0), ellipsis, font=font)
        ellipsis_width = ellipsis_bbox[2] - ellipsis_bbox[0]
        available_width = max_width - ellipsis_width
        
        # Binary search for the longest text that fits
        left, right = 0, len(text)
        best_length = 0
        
        while left <= right:
            mid = (left + right) // 2
            test_text = text[:mid]
            test_bbox = draw.textbbox((0, 0), test_text, font=font)
            test_width = test_bbox[2] - test_bbox[0]
            
            if test_width <= available_width:
                best_length = mid
                left = mid + 1
            else:
                right = mid - 1
        
        return text[:best_length] + ellipsis

    def render(self, img, draw, font, width, height):
        """Render the screen with menu centered."""
        if not self._media_player.current_song:
            return None

        text_max_width = width - self.padding_left - self.padding_right
        bbox = draw.textbbox((0, 0), "A", font=font)
        line_height = bbox[3] - bbox[1]

        texts = [
            Path(self._media_player.current_song.name).stem,
            self._media_player.current_song.album or "",
            self._media_player.current_song.artist or ""
        ]

        y = self.padding_top + SCREEN_SIZE / 3

        for i, item_text in enumerate(texts):
            full_text_width = draw.textbbox((0, 0), item_text, font=font)[2]

            # Only do marquee if text is too wide
            if full_text_width > text_max_width:
                current_time = time.time()
                if current_time - self.last_title_shift_times[i] > self.title_shift_interval:
                    self.title_offsets[i] = (self.title_offsets[i] + 1) % (len(item_text) + 10)
                    self.last_title_shift_times[i] = current_time

                # Seamless scrolling
                gap = " " * 6
                scroll_text = item_text + gap + item_text
                start = self.title_offsets[i] % len(scroll_text)
                visible_text = scroll_text[start : start + len(item_text) + len(gap)]

                # Truncate to fit
                item_text = self._truncate_text(visible_text, text_max_width, draw, font, ellipsis="")
            else:
                # Optional: reset offset when text becomes short again
                self.title_offsets[i] = 0

            # Draw the (possibly scrolled) text
            draw.text((self.padding_left, y), item_text, fill=(255, 255, 255), font=font)
            y += line_height + 2

        self.controls.render(img, draw)

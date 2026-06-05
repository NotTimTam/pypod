import time

from pathlib import Path

from src.utils.media_player import PlayerStatus
from src.utils.constants import SCREEN_SIZE

class NowPlayingWidget():
    def __init__(self, media_player=None):
        self._media_player = media_player

        self.title_offset = 0
        self.last_title_shift_time = 0
        self.title_shift_interval = 0.2

        # Toggle between now playing and "Hold A" message
        self.last_switch_time = 0
        self.switch_interval = 10.0          # 10 seconds
        self.show_details_prompt = True

    def _truncate_text(self, text, max_width, draw, font):
        """
        Truncate text to fit within max_width.
        
        Args:
            text: Text to truncate
            max_width: Maximum width in pixels
            draw: PIL ImageDraw object
            font: PIL ImageFont
            
        Returns:
            Truncated text that fits within max_width
        """
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            return text
        
        # Binary search for the longest text that fits
        left, right = 0, len(text)
        best_length = 0
        
        while left <= right:
            mid = (left + right) // 2
            test_text = text[:mid]
            test_bbox = draw.textbbox((0, 0), test_text, font=font)
            test_width = test_bbox[2] - test_bbox[0]
            
            if test_width <= max_width:
                best_length = mid
                left = mid + 1
            else:
                right = mid - 1
        
        return text[:best_length]

    def render(self, img, draw, font):
        """Render the screen with menu centered."""
        if (not self._media_player.current_song) or (self._media_player.get_status() == PlayerStatus.STOPPED):
            return None

        current_time = time.time()

        # Toggle between the two messages every 10 seconds
        if current_time - self.last_switch_time > self.switch_interval:
            self.show_details_prompt = not self.show_details_prompt
            self.last_switch_time = current_time
            # Reset marquee when switching message
            self.title_offset = 0

        text_max_width = SCREEN_SIZE
        bbox = draw.textbbox((0, 0), "A", font=font)
        line_height = bbox[3] - bbox[1]

        # Choose which text to display
        if self.show_details_prompt:
            display = "Hold A for more details..."
        else:
            song_name = Path(self._media_player.current_song.name).stem
            album = self._media_player.current_song.album or ""
            artist = self._media_player.current_song.artist or ""
            display = f"Now playing: {song_name} / {album} / {artist}"

        # === Marquee logic (now applies to both texts) ===
        full_text_width = draw.textbbox((0, 0), display, font=font)[2]

        if full_text_width > text_max_width:
            if current_time - self.last_title_shift_time > self.title_shift_interval:
                self.title_offset = (self.title_offset + 1) % (len(display) + 10)
                self.last_title_shift_time = current_time

            gap = " " * 6
            scroll_text = display + gap + display
            start = self.title_offset % len(scroll_text)
            visible_text = scroll_text[start : start + len(display) + len(gap)]
            
            display = self._truncate_text(visible_text, text_max_width, draw, font)
        else:
            self.title_offset = 0

        # Draw separator line + text
        draw.line((0, SCREEN_SIZE - line_height - 6, SCREEN_SIZE, SCREEN_SIZE - line_height - 6), 
                  fill=(255, 255, 255), width=1)
        draw.text((0, SCREEN_SIZE - line_height - 4), display, fill=(255, 255, 255), font=font)
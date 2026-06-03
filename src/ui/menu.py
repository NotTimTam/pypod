import time
from src.utils.input import input_handler
from src.ui.menu_items import MenuItem, SongMenuItem, AlbumMenuItem


class Menu:
    """Manages menu options, navigation, and rendering."""

    def __init__(self, items=None, state=None):
        self.items = items or []
        self.current_index = 0
        self.title_offset = 0
        self.last_title_shift_time = 0
        self.title_shift_interval = 0.2  # seconds between character shifts
        if state:
            self.set_state(state)

    def add_item(self, text, callback):
        """Add a menu item."""
        self.items.append(MenuItem(text, callback))

    def move_up(self):
        """Move selection up."""
        if self.items:
            self.current_index = (self.current_index - 1) % len(self.items)

    def move_down(self):
        """Move selection down."""
        if self.items:
            self.current_index = (self.current_index + 1) % len(self.items)

    def select_current(self):
        """Execute callback for current item."""
        if self.items and self.current_index < len(self.items):
            self.items[self.current_index].callback()

    def handle_input(self):
        input_handler.handle_button("X", self.move_up)
        input_handler.handle_button("Y", self.move_down)
        input_handler.handle_button("A", self.select_current)

    def render(self, img, draw, font, x, y, width, height, download_manager=None):
        """
        Render menu at specified position.

        Args:
            img: PIL Image object
            draw: PIL ImageDraw object
            font: PIL ImageFont
            x, y: Top-left position for menu
            width, height: Available space for menu
            download_manager: Optional DownloadManager for progress tracking
        """
        if not self.items:
            return

        # Calculate item height
        bbox = draw.textbbox((0, 0), "A", font=font)
        line_height = bbox[3] - bbox[1]
        padding = 4

        # Calculate visible items count and scroll offset
        item_height = line_height + padding
        visible_count = max(1, height // item_height)
        total_height = len(self.items) * item_height

        # Calculate scroll offset to keep current item visible
        scroll_offset = 0
        if total_height > height:
            # Center the current item if possible
            ideal_offset = max(0, (self.current_index * item_height) - (height // 2) + (item_height // 2))
            scroll_offset = min(ideal_offset, total_height - height)

        # Get download state if manager provided
        download_state = None
        if download_manager:
            download_state = download_manager.get_state()

        # Render each visible item
        for i, item in enumerate(self.items):
            item_y = y + (i * item_height) - scroll_offset

            # Skip items outside visible area
            if item_y + item_height < y or item_y > y + height:
                continue

            is_selected = i == self.current_index
            item_text = item.text

            # Handle marquee for long titles
            text_width = draw.textbbox((0, 0), item_text, font=font)[2]
            if is_selected and text_width > width - 8:
                # Animate title scroll
                current_time = time.time()
                if current_time - self.last_title_shift_time > self.title_shift_interval:
                    self.title_offset = (self.title_offset + 1) % (len(item_text) + 5)
                    self.last_title_shift_time = current_time

                # Create scrolling text
                scroll_text = item_text[self.title_offset:] + "     " + item_text[:self.title_offset]
                item_text = scroll_text[:len(item_text)]

            # Draw progress bar background for SongMenuItems being downloaded
            if isinstance(item, SongMenuItem) and download_state and download_state["current_download_id"] == item.song_id and download_state["current_status"] == "downloading":
                progress_width = int((width * download_state["current_progress"]) / 100)
                draw.rectangle(
                    (x, item_y, x + progress_width, item_y + item_height),
                    fill=(0, 255, 0)
                )

            # Draw background for selected item
            if is_selected:
                draw.rectangle(
                    (x, item_y, x + width, item_y + item_height),
                    fill=(255, 255, 255)
                )
                text_color = (0, 0, 0)
            else:
                text_color = (255, 255, 255)

            # Draw text
            text_x = x + 4
            draw.text((text_x, item_y), item_text, fill=text_color, font=font)

            # Draw duration and status for SongMenuItems
            if isinstance(item, SongMenuItem):
                duration_text = f"{item.duration_sec // 60}:{item.duration_sec % 60:02d}"
                duration_bbox = draw.textbbox((0, 0), duration_text, font=font)
                duration_width = duration_bbox[2] - duration_bbox[0]

                # Draw duration
                duration_x = x + width - duration_width - 4
                draw.text((duration_x, item_y), duration_text, fill=text_color, font=font)

                # Draw checkmark if downloaded
                if item.downloaded:
                    checkmark = "✓"
                    checkmark_bbox = draw.textbbox((0, 0), checkmark, font=font)
                    checkmark_width = checkmark_bbox[2] - checkmark_bbox[0]
                    checkmark_x = duration_x - checkmark_width - 8
                    draw.text((checkmark_x, item_y), checkmark, fill=text_color, font=font)

    def get_state(self):
        """Return dict of menu state for persistence."""
        return {"current_index": self.current_index}

    def set_state(self, state):
        """Restore menu state from dict."""
        if state and "current_index" in state:
            self.current_index = state["current_index"]

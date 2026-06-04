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

    def render(self, img, draw, font, x, y, width, height, download_manager=None):
        """
        Render menu at specified position, only rendering visible items.

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
        item_height = line_height + padding

        # Calculate scroll offset to keep current item visible
        total_height = len(self.items) * item_height
        scroll_offset = 0
        if total_height > height:
            # Center the current item if possible
            ideal_offset = max(0, (self.current_index * item_height) - (height // 2) + (item_height // 2))
            scroll_offset = min(ideal_offset, total_height - height)

        # Calculate visible range (OPTIMIZATION: only render visible items)
        first_visible_index = max(0, scroll_offset // item_height)
        last_visible_index = min(len(self.items), (scroll_offset + height) // item_height + 1)

        # Get download state if manager provided
        download_state = None
        if download_manager:
            download_state = download_manager.get_state()

        # Render only visible items
        for i in range(first_visible_index, last_visible_index):
            if i >= len(self.items):
                break
                
            item = self.items[i]
            item_y = y + (i * item_height) - scroll_offset
            is_selected = i == self.current_index
            item_text = item.text

            # Calculate available width for text based on item type
            text_max_width = width - 8  # Default: 4px left padding + 4px right padding

            # For SongMenuItems, reserve space for duration and checkmark on the right
            if isinstance(item, SongMenuItem):
                duration_text = f"{item.duration_sec // 60}:{item.duration_sec % 60:02d}"
                duration_bbox = draw.textbbox((0, 0), duration_text, font=font)
                duration_width = duration_bbox[2] - duration_bbox[0]
                
                # Space needed: duration + checkmark (if present) + padding
                right_space_needed = duration_width + 4  # duration + padding
                if item.downloaded:
                    checkmark_bbox = draw.textbbox((0, 0), "✓", font=font)
                    checkmark_width = checkmark_bbox[2] - checkmark_bbox[0]
                    right_space_needed += checkmark_width + 8  # checkmark + padding
                
                text_max_width = width - 4 - right_space_needed

            # Handle text: marquee if selected, truncate if not
            if is_selected:
                full_text_width = draw.textbbox((0, 0), item_text, font=font)[2]
                
                if full_text_width > text_max_width:
                    current_time = time.time()
                    if current_time - self.last_title_shift_time > self.title_shift_interval:
                        self.title_offset = (self.title_offset + 1) % (len(item_text) + 10)  # +10 for comfortable gap
                        self.last_title_shift_time = current_time

                    # Create seamless scrolling text
                    gap = " " * 6
                    scroll_text = item_text + gap + item_text
                    
                    # Get current position
                    start = self.title_offset % len(scroll_text)
                    visible_text = scroll_text[start:start + len(item_text) + len(gap)]

                    # Now force it to fit within text_max_width (no ellipsis for marquee)
                    item_text = self._truncate_text(visible_text, text_max_width, draw, font, ellipsis="")
                else:
                    item_text = item_text  # no need to scroll
            else:
                # Truncate text if it doesn't fit and item is not selected
                item_text = self._truncate_text(item_text, text_max_width, draw, font)

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

            # Draw main text
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
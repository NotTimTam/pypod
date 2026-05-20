import pygame
from typing import Optional, List, Tuple
from ..utils.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLORS
from ..utils.image_handler import load_image_from_bytes, stretch_image_to_screen


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_large = pygame.font.SysFont('Segoe UI Symbol', 28)
        self.font_normal = pygame.font.SysFont('Segoe UI Symbol', 20)
        self.font_small = pygame.font.SysFont('Segoe UI Symbol', 16)
        self.bg_image: Optional[pygame.Surface] = None

        self.marquee_text: str = ""
        self.marquee_text_width: int = 0
        self.marquee_start_ticks: int = pygame.time.get_ticks()
        self.marquee_speed: int = 20  # pixels per second

    def set_background_image(self, image_bytes: Optional[bytes]) -> None:
        """Set background image from bytes."""
        if image_bytes:
            surface = load_image_from_bytes(image_bytes, SCREEN_WIDTH)
            if surface:
                self.bg_image = stretch_image_to_screen(surface, SCREEN_WIDTH, SCREEN_HEIGHT)
        else:
            self.bg_image = None

    def clear(self) -> None:
        """Clear screen with background."""
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(COLORS["black"])

    def draw_header(self, text: str) -> int:
        """Draw header text, return height used."""
        surf = self.font_large.render(text, True, COLORS["yellow"])
        self.screen.blit(surf, (5, 5))
        return 30

    def draw_subheader(self, text: str, y: int) -> int:
        """Draw subheader text, return height used."""
        surf = self.font_normal.render(text, True, COLORS["gray"])
        self.screen.blit(surf, (5, y))
        return 20

    def draw_list(
        self,
        items: List[str],
        start_y: int,
        selected_index: int,
        max_items: int = 9,
        offset: int = 0,
    ) -> int:
        """Draw list of items, return total height used. offset allows scrolling."""
        item_height = 20
        visible_items = items[offset : offset + max_items]

        for i, item in enumerate(visible_items):
            y = start_y + i * item_height
            is_selected = i + offset == selected_index
            color = COLORS["yellow"] if is_selected else COLORS["white"]
            prefix = "> " if is_selected else "  "

            text = f"{prefix}{item}"
            surf = self.font_normal.render(text, True, color)
            self.screen.blit(surf, (5, y))

        return len(visible_items) * item_height

    def draw_now_playing(self, song_name: str, artist_name: str) -> None:
        """Draw now playing with marquee text."""
        text = f"► {song_name} — {artist_name}"
        text_width, text_height = self.font_small.size(text)
        available_width = SCREEN_WIDTH - 10

        if text != self.marquee_text or text_width != self.marquee_text_width:
            self.marquee_text = text
            self.marquee_text_width = text_width
            self.marquee_start_ticks = pygame.time.get_ticks()

        x = 5
        if text_width > available_width:
            scroll_range = text_width - available_width
            elapsed = (pygame.time.get_ticks() - self.marquee_start_ticks) / 1000.0
            period = 2 * scroll_range / self.marquee_speed if self.marquee_speed > 0 else 0.0
            if period > 0:
                position = (elapsed * self.marquee_speed) % (2 * scroll_range)
                if position > scroll_range:
                    position = 2 * scroll_range - position
                x = 5 - int(position)

        surf = self.font_small.render(text, True, COLORS["yellow"])
        self.screen.blit(surf, (x, SCREEN_HEIGHT - text_height - 5))

    def draw_now_playing_screen(
        self,
        song_name: str,
        artist_name: str,
        album_name: str,
        current: int,
        total: int,
        is_playing: bool,
        shuffle_enabled: bool,
    ) -> None:
        """Draw full now playing screen."""
        # Song title
        title_surf = self.font_large.render(song_name, True, COLORS["white"])
        self.screen.blit(title_surf, (5, 30))

        # Artist and album
        info_surf = self.font_normal.render(f"{artist_name}", True, COLORS["gray"])
        self.screen.blit(info_surf, (5, 60))

        album_surf = self.font_normal.render(f"{album_name}", True, COLORS["gray"])
        self.screen.blit(album_surf, (5, 80))

        # Status
        status = "►Playing" if is_playing else "⏸Paused"
        status_surf = self.font_normal.render(status, True, COLORS["yellow"])
        self.screen.blit(status_surf, (5, 140))

        # Shuffle
        shuffle_status = "🔀Shuffle ON" if shuffle_enabled else "🔀Shuffle OFF"
        shuffle_surf = self.font_small.render(shuffle_status, True, COLORS["gray"])
        self.screen.blit(shuffle_surf, (5, 160))

        # Controls hint
        hint_surf = self.font_small.render("▲Prev  ▼Next  ▶Play  ◀Back", True, COLORS["gray"])
        self.screen.blit(hint_surf, (5, 210))

    def draw_centered_text(self, text: str, y: int, color: Tuple[int, int, int] = COLORS["white"]) -> None:
        """Draw centered text."""
        surf = self.font_normal.render(text, True, color)
        x = (SCREEN_WIDTH - surf.get_width()) // 2
        self.screen.blit(surf, (x, y))

    def draw_tooltip(self, text: str) -> None:
        """Draw tooltip at top center."""
        surf = self.font_small.render(text, True, COLORS["yellow"])
        x = (SCREEN_WIDTH - surf.get_width()) // 2
        self.screen.blit(surf, (x, 5))

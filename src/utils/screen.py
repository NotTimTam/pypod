from abc import ABC, abstractmethod

class Screen(ABC):
    """Base class for all screens in the navigation system."""

    def __init__(self, padding_top=0, padding_bottom=0, padding_left=0, padding_right=0):
        self.padding_top = padding_top
        self.padding_bottom = padding_bottom
        self.padding_left = padding_left
        self.padding_right = padding_right

    def handle_input(self, button):
        """Handle input for this screen. Override in subclasses."""
        pass

    @abstractmethod
    def render(self, img, draw, font, width, height):
        """Render the screen content. Must be implemented by subclasses."""
        pass

    def get_state(self):
        """Return dict of screen state. Override in subclasses for persistence."""
        return {}

    def set_state(self, state):
        """Restore state from dict. Override in subclasses."""
        pass

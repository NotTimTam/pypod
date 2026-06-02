from src.utils.screen import Screen
from src.utils.menu import Menu

class HomeScreen(Screen):
    """Home screen with navigation menu."""

    def __init__(self, state=None):
        super().__init__(
            padding_top=12,
            padding_bottom=12,
            padding_left=0,
            padding_right=0
        )
        menu_state = state.get("menu", {}) if state else {}
        self.menu = Menu(state=menu_state)
        self._setup_menu()

    def _setup_menu(self):
        """Define menu items and their callbacks."""
        self.menu.add_item("Battery", self._on_battery)
        self.menu.add_item("Settings", self._on_settings)
        self.menu.add_item("About", self._on_about)

    def _on_battery(self):
        print("Battery screen selected")

    def _on_settings(self):
        print("Settings screen selected")

    def _on_about(self):
        print("About screen selected")

    def handle_input(self):
        """Handle input."""
        self.menu.handle_input()
        
    def render(self, img, draw, font, width, height):
        """Render the home screen with menu centered."""
        # Calculate center position for menu
        content_width = width - self.padding_left - self.padding_right
        content_height = height - self.padding_top - self.padding_bottom
        menu_width = content_width - 8
        menu_height = content_height
        menu_x = self.padding_left + 4
        menu_y = self.padding_top

        # Render menu
        self.menu.render(img, draw, font, menu_x, menu_y, menu_width, menu_height)

    def get_state(self):
        """Return screen state for persistence."""
        return {
            "menu": self.menu.get_state()
        }

    def set_state(self, state):
        """Restore screen state from dict."""
        if state and "menu" in state:
            self.menu.set_state(state["menu"])

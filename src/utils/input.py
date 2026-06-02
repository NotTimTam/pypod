import os
os.environ["GPIOZERO_PIN_FACTORY"] = "lgpio"

from gpiozero import Button
import atexit

class ButtonState:
    """Holds the current pressed state of each button"""
    def __init__(self):
        self.A = False
        self.B = False
        self.X = False
        self.Y = False

    def reset(self):
        self.A = self.B = self.X = self.Y = False

    def __repr__(self):
        return f"Buttons(A={self.A}, B={self.B}, X={self.X}, Y={self.Y})"

class InputHandler:
    def __init__(self):
        self.BUTTONS = [5, 6, 16, 24]
        self.LABELS = ['A', 'B', 'X', 'Y']
        self.PIN_TO_LABEL = dict(zip(self.BUTTONS, self.LABELS))
        self.LAST_BUTTON = '_'
        self.state = ButtonState()

        self._buttons = {}
        for pin, label in self.PIN_TO_LABEL.items():
            b = Button(pin, pull_up=True, bounce_time=0.06)  # bounce_time in seconds
            b.when_pressed  = lambda l=label: self._pressed(l)
            b.when_released = lambda l=label: self._released(l)
            self._buttons[pin] = b
            print(f"DEBUG: Pin {pin} ({label}) OK")

        atexit.register(self.cleanup)

    def _pressed(self, label):
        self.LAST_BUTTON = label
        setattr(self.state, label, True)

    def _released(self, label):
        setattr(self.state, label, False)

    def cleanup(self):
        for b in self._buttons.values():
            b.close()

# Global instance (easy to import)
input_handler = InputHandler()
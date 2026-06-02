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
        self.event_queue = []

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
        self.event_queue.append(('pressed', label))

    def _released(self, label):
        setattr(self.state, label, False)
        self.event_queue.append(('released', label))

    def button_state(self, button_label):
        """Return whether the named button is currently pressed.

        Accepts case-insensitive labels like 'A', 'a', 'B', etc.
        """
        label = str(button_label).upper()
        if label not in self.LABELS:
            raise ValueError(f"Unknown button label: {button_label}")
        return getattr(self.state, label)

    def dequeue(self):
        """Get next event from queue, or None if empty."""
        return self.event_queue.pop(0) if self.event_queue else None

    def has_events(self):
        """Check if there are pending events."""
        return len(self.event_queue) > 0

    def process_events(self, callback):
        """Process events by calling callback(event_type, button) for each.
        Only dequeues events where callback returns True (handled).
        """
        while self.has_events():
            event = self.event_queue[0]
            if callback(*event):
                self.event_queue.pop(0)
            else:
                break

    def handle_button(self, button, callback):
        """If button was pressed, call callback and consume the event."""
        button = button.upper()
        while self.has_events():
            event_type, btn = self.event_queue[0]
            if event_type == 'pressed' and btn == button:
                callback()
                self.event_queue.pop(0)
                return True
            else:
                break
        return False

    def cleanup(self):
        for b in self._buttons.values():
            b.close()

# Global instance (easy to import)
input_handler = InputHandler()
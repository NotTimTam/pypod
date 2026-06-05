import os
os.environ["GPIOZERO_PIN_FACTORY"] = "lgpio"
from gpiozero import Button
import atexit
import time

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
    
        # Long press tracking
        self.press_times = {}
        self.long_press_triggered = {}
        self.long_press_callbacks = {}
        self.long_press_duration = 2.0
    
        # Activity callback for sleep/wake
        self.activity_callback = None
    
        for pin, label in self.PIN_TO_LABEL.items():
            b = Button(pin, pull_up=True, bounce_time=0.06)
            b.when_pressed  = lambda l=label: self._pressed(l)
            b.when_released = lambda l=label: self._released(l)
            self._buttons[pin] = b
            self.long_press_triggered[label] = False
            print(f"DEBUG: Pin {pin} ({label}) OK")
        atexit.register(self.cleanup)

    def _pressed(self, label):
        self.LAST_BUTTON = label
        setattr(self.state, label, True)
        self.press_times[label] = time.time()
        self.long_press_triggered[label] = False
        if self.activity_callback:
            self.activity_callback(label)

    def _released(self, label):
        setattr(self.state, label, False)
        if label not in self.press_times:
            return
        if not self.long_press_triggered[label]:
            self.event_queue.append(label)
        del self.press_times[label]
        self.long_press_triggered[label] = False
        if self.activity_callback:
            self.activity_callback(label)

    def register_long_press(self, button_label, callback, duration=2.0):
        label = str(button_label).upper()
        if label not in self.LABELS:
            raise ValueError(f"Unknown button label: {button_label}")
        self.long_press_callbacks[label] = callback
        self.long_press_duration = duration

    def check_long_presses(self):
        current_time = time.time()
        for label, press_time in list(self.press_times.items()):
            if (
                current_time - press_time >= self.long_press_duration
                and not self.long_press_triggered[label]
                and label in self.long_press_callbacks
            ):
                self.long_press_triggered[label] = True
                self.long_press_callbacks[label]()

    def button_state(self, button_label):
        label = str(button_label).upper()
        if label not in self.LABELS:
            raise ValueError(f"Unknown button label: {button_label}")
        return getattr(self.state, label)

    def dequeue(self):
        return self.event_queue.pop(0) if self.event_queue else None

    def has_events(self):
        return len(self.event_queue) > 0

    def process_events(self, callback):
        while self.has_events():
            event = self.event_queue[0]
            if callback(*event):
                self.event_queue.pop(0)
            else:
                break

    def handle_button(self, button, callback):
        button = button.upper()
        for i, btn in enumerate(self.event_queue):
            if btn == button:
                callback()
                self.event_queue.pop(i)
                return True
        return False

    def register_activity_callback(self, callback):
        """Register a callback to be called on any button press/release."""
        self.activity_callback = callback

    def clear_events(self):
        """Clear all pending button events and reset states.
        Used when waking from sleep to prevent accidental actions."""
        self.event_queue.clear()
        self.state.reset()
        self.press_times.clear()
        for label in self.LABELS:
            self.long_press_triggered[label] = False

    def cleanup(self):
        for b in self._buttons.values():
            b.close()

# Global instance
input_handler = InputHandler()
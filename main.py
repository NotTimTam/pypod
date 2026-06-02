#!/usr/bin/env python3

from dotenv import load_dotenv

import os
import sys
import st7789
import signal
import traceback

from PIL import Image, ImageDraw, ImageFont

from src.utils.constants import SCREEN_SIZE
from src.utils.device import get_battery_status, start_device_thread

#########################################

# Load environment
load_dotenv()
LIBRARY = os.getenv("LIBRARY")

if not LIBRARY:
    raise ValueError("No LIBRARY env variable defined")


# Begin polling for battery data
start_device_thread()

# Create ST7789 LCD display class.
disp = st7789.ST7789(
    height= SCREEN_SIZE,
    rotation= 90,
    port=0,
    cs=st7789.BG_SPI_CS_FRONT,  # BG_SPI_CS_BACK or BG_SPI_CS_FRONT
    dc=9,
    backlight=13,  
    spi_speed_hz=80 * 1000 * 1000,
    offset_left=0,
    offset_top=0,
)

# Initialize display.
disp.begin()

WIDTH = disp.width
HEIGHT = disp.height

def cleanup():
    """Clear display and turn off backlight."""
    blank = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    disp.display(blank)
    disp.set_backlight(0)

def handle_signal(sig, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

def load_screen(name, state=None):
    """Factory function to load screens by name."""
    if name == "home":
        from src.screens.home import HomeScreen as _HomeScreen
        return _HomeScreen(state=state)
    elif name == "music":
        from src.screens.music import MusicScreen as _MusicScreen
        return _MusicScreen(state=state)
    else:
        raise ValueError(f"Unknown screen: {name}")

img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)

bbox = draw.textbbox((0, 0), "A", font=font)
size_y = bbox[3] - bbox[1]

text_x = int(0)
text_y = int(disp.height - size_y - 4)

# Screen state management
current_screen_name = "home"
current_screen = load_screen(current_screen_name, {}, load_screen)

try:
    while True:
        status = get_battery_status()

        # Clear display
        draw.rectangle((0, 0, disp.width, disp.height), (0, 0, 0))

        current_screen.handle_input()

        # Render screen
        current_screen.render(img, draw, font, WIDTH, HEIGHT)

        # Render battery info in bottom bar (doesn't interfere with screen content)
        plug = "+" if status['is_plugged'] else ""
        draw.text((text_x, text_y), f"{status['battery_pct']:.1f}%{plug} | {status['voltage']:.2f}V", fill=(255, 255, 255), font=font)
        
        disp.display(img)

except Exception as e:
    traceback.print_exc(file=sys.stderr)
finally:
    cleanup()
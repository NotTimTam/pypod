#!/usr/bin/env python3

from dotenv import load_dotenv

import os
import sys
import st7789
import signal
import traceback

from PIL import Image, ImageDraw, ImageFont

from src.utils.constants import SCREEN_SIZE
from src.utils.device import start_device_thread
from src.utils.jellyfin import Jellyfin
from src.utils.download_manager import DownloadManager
from src.utils.media_player import MediaPlayer
from src.utils.input import input_handler

#########################################

# Load environment
load_dotenv()
LIBRARY = os.getenv("LIBRARY")

if not LIBRARY:
    raise ValueError("No LIBRARY env variable defined")

JELLYFIN_URL = os.getenv("JELLYFIN_URL")

if JELLYFIN_URL:
    JELLYFIN_LIBRARY  = os.getenv("JELLYFIN_LIBRARY")
    JELLYFIN_USERNAME = os.getenv("JELLYFIN_USERNAME")
    JELLYFIN_PASSWORD = os.getenv("JELLYFIN_PASSWORD")
    if not (JELLYFIN_LIBRARY and JELLYFIN_USERNAME and JELLYFIN_PASSWORD):
        raise ValueError("JELLYFIN_URL configured but missing JELLYFIN_USERNAME, JELLYFIN_PASSWORD and/or JELLYFIN_LIBRARY")
    jellyfin = Jellyfin(JELLYFIN_URL, JELLYFIN_USERNAME, JELLYFIN_PASSWORD, JELLYFIN_LIBRARY, download_root=LIBRARY + "/music")
    download_manager = DownloadManager(jellyfin=jellyfin)
else:
    jellyfin = None
    download_manager = None

media_player = MediaPlayer(music_dir=LIBRARY + "/music")

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
    """Cleanup application on exit."""
    media_player.cleanup()
    
    blank = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    disp.display(blank)
    disp.set_backlight(0)

def handle_signal(sig, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

requested_screen="home"
requested_state = None

def request_screen(name, state=None):
    global requested_screen 
    global requested_state
    requested_screen = name
    requested_state = state

def load_screen(name, state=None):
    """Factory function to load screens by name."""
    if name == "home":
        from src.screens.home import HomeScreen as _HomeScreen
        return _HomeScreen(state=state, request_screen=request_screen, jellyfin=True)
    elif name == "music":
        from src.screens.music import MusicScreen as _MusicScreen
        return _MusicScreen(state=state, request_screen=request_screen)
    elif name == "artists":
        from src.screens.artists import ArtistScreen as _ArtistScreen
        return _ArtistScreen(state=state, request_screen=request_screen, music_dir=LIBRARY + "/music", media_player=media_player)
    elif name == "albums":
        from src.screens.albums import AlbumScreen as _AlbumScreen
        return _AlbumScreen(state=state, request_screen=request_screen, music_dir=LIBRARY + "/music", media_player=media_player)
    elif name == "songs":
        from src.screens.songs import SongScreen as _SongScreen
        return _SongScreen(state=state, request_screen=request_screen, music_dir=LIBRARY + "/music", media_player=media_player)
    elif name == "now_playing":
        from src.screens.now_playing import NowPlayingScreen as _NowPlayingScreen
        return _NowPlayingScreen(state=state, request_screen=request_screen, music_dir=LIBRARY + "/music", media_player=media_player)
    elif name == "settings":
        from src.screens.settings import SettingsScreen as _SettingsScreen
        return _SettingsScreen(state=state, request_screen=request_screen)
    elif name == "jellyfin":
        from src.screens.jellyfin import JellyfinScreen as _JellyfinScreen
        return _JellyfinScreen(state=state, request_screen=request_screen, jellyfin=jellyfin, download_manager=download_manager)
    elif name == "jellyfin_artists":
        from src.screens.jellyfin_artists import JellyfinArtistsScreen as _JellyfinArtistsScreen
        return _JellyfinArtistsScreen(state=state, request_screen=request_screen, jellyfin=jellyfin, download_manager=download_manager)
    elif name == "jellyfin_albums":
        from src.screens.jellyfin_albums import JellyfinAlbumsScreen as _JellyfinAlbumsScreen
        return _JellyfinAlbumsScreen(state=state, request_screen=request_screen, jellyfin=jellyfin, download_manager=download_manager)
    elif name == "jellyfin_songs":
        from src.screens.jellyfin_songs import JellyfinSongsScreen as _JellyfinSongsScreen
        return _JellyfinSongsScreen(state=state, request_screen=request_screen, jellyfin=jellyfin, download_manager=download_manager)
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
current_screen = load_screen(current_screen_name, {})

def on_a_long_press():
    """Called when A button is held for 2+ seconds"""
    request_screen("now_playing")
 
input_handler.register_long_press('A', on_a_long_press, duration=2.0)


try:
    while True:
        if (current_screen_name != "now_playing"):
            input_handler.check_long_presses()

        if (requested_screen):
            current_screen_name = requested_screen
            current_screen = load_screen(current_screen_name, requested_state)
            requested_state = None
            requested_screen = None

        # Clear display
        draw.rectangle((0, 0, disp.width, disp.height), (0, 0, 0))

        current_screen.handle_input()

        # Render screen
        current_screen.render(img, draw, font, WIDTH, HEIGHT)

        disp.display(img)

except Exception as e:
    traceback.print_exc(file=sys.stderr)
finally:
    cleanup()
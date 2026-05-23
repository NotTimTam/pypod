#!/usr/bin/env python3

from dotenv import load_dotenv

import os
import sys
import time
import st7789

from PIL import Image, ImageDraw, ImageFont

from src.utils.input import input_handler

#########################################

# Load environment
load_dotenv()
LIBRARY = os.getenv("LIBRARY")

if not LIBRARY:
    raise ValueError("No LIBRARY env variable defined")

# Create ST7789 LCD display class.
disp = st7789.ST7789(
    height= 240,
    rotation= 0, # 90
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

img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))

draw = ImageDraw.Draw(img)

# font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)

size_x, size_y = draw.textsize("A")

text_x = int(disp.width - size_x)
text_y = int(disp.height - size_y)

t_start = time.time()

while True:
    x = disp.width / 2
    draw.rectangle((0, 0, disp.width, disp.height), (0, 0, 0)) # Clear display.
    draw.text((text_x, text_y), input_handler.LAST_BUTTON or "_", fill=(255, 255, 255))
    disp.display(img)

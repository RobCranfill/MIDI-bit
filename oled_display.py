import board
import displayio
from displayio import I2CDisplay as I2CDisplayBus

import terminalio

from adafruit_display_text import label
import adafruit_displayio_ssd1306

import time


class oled_display:

    def __init__(self):

        print("Creating oled_display...")

        displayio.release_displays()

        i2c = board.I2C()  # uses board.SCL and board.SDA
        display_bus = I2CDisplayBus(i2c, device_address=0x3C)

        WIDTH = 128
        HEIGHT = 32  # Change to 64 if needed

        display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

        # Make the display context
        splash = displayio.Group()
        display.root_group = splash

        color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
        color_palette = displayio.Palette(1)
        color_palette[0] = 0x000000  # black
        bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
        splash.append(bg_sprite)

        # Create the label
        text = "Hello World!"
        self.text_area = label.Label(terminalio.FONT, text=text, color=0xFFFFFF, x=28, y=HEIGHT // 2 - 1)
        splash.append(self.text_area)

    def set_text(self, text):
        self.text_area._set_text(text, 1.0)

    def test(self):

        self.set_text("One!")
        time.sleep(1)
        self.set_text("Two!")
        time.sleep(1)
        self.set_text("Three!")

        print("test done")
        # while True:
        #     pass


# disp = oled_display()
# disp.test()
# while True:
#     pass


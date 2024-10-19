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
        HEIGHT = 32

        display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

        # Make the display context
        root = displayio.Group()
        display.root_group = root

        # clear the screen to black
        color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
        color_palette = displayio.Palette(1)
        color_palette[0] = 0x000000  # black
        bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
        root.append(bg_sprite)

        # Create the labels
        LINE_HEIGHT = 10
        x = 0
        y = 5
        self.text_area_1 = label.Label(terminalio.FONT, color=0xFFFFFF, x=x, y=y)
        root.append(self.text_area_1)

        y += LINE_HEIGHT
        self.text_area_2 = label.Label(terminalio.FONT, color=0xFFFFFF, x=x, y=y)
        root.append(self.text_area_2)

        y += LINE_HEIGHT
        self.text_area_3 = label.Label(terminalio.FONT, color=0xFFFFFF, x=x, y=y)
        root.append(self.text_area_3)

        # y += LINE_HEIGHT
        # self.text_area_4 = label.Label(terminalio.FONT, color=0xFFFFFF, x=x, y=y)
        # root.append(self.text_area_4)


    def set_text_1(self, text):
        self.text_area_1._set_text(text, 2.0)

    def set_text_2(self, text):
        self.text_area_2._set_text(text, 1.0)

    def set_text_3(self, text):
        self.text_area_3._set_text(text, 1.0)

    # def set_text_4(self, text):
    #     self.text_area_4._set_text(text, 1.0)


    def test(self):

        self.set_text_1("This is a test.")
        self.set_text_2("This is only a test.")
        self.set_text_3("1234567890123456789012345")

        time.sleep(1)
        self.set_text_1("This was a test.")
    
        time.sleep(1)
        self.set_text_1("This will be a test.")

        print("test done")
        # while True:
        #     pass


# disp = oled_display()
# disp.test()
# while True:
#     pass


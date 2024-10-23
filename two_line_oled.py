# Nice two-line display on the 128x32 OLED display

import board
import displayio
import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_displayio_ssd1306


class two_line_oled:

    def __init__(self):

        displayio.release_displays()
        i2c = board.I2C()
        display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
        WIDTH = 128
        HEIGHT = 32
        display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

        font16 = bitmap_font.load_font("fonts/LeagueSpartan-Bold-16.bdf")

        text_area_1 = label.Label(font16, color=0xFFFFFF)
        text_area_1.x =  0
        text_area_1.y = 10

        text_area_2 = label.Label(terminalio.FONT, color=0xFFFFFF)
        text_area_2.x =  0
        text_area_2.y = 28

        root = displayio.Group()
        display.root_group = root
        root.append(text_area_1)
        root.append(text_area_2)

        self.text_area_1 = text_area_1
        self.text_area_2 = text_area_2


    def set_text_1(self, text):
        self.text_area_1.text = text
        
    def set_text_2(self, text):
        self.text_area_2.text = text


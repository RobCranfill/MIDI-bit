# Nice two-line display on the 128x32 OLED display

import board
import displayio
import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_displayio_ssd1306


# FONT_PATH = "fonts/LeagueSpartan-Bold-22.bdf"
FONT_PATH = "fonts/cmuntb22.bdf"


class one_line_oled:

    def __init__(self):

        displayio.release_displays()

        try:
            i2c = board.I2C()
        except:
            print("Is the I2C wiring correct?")
            return

        display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
        WIDTH = 128
        HEIGHT = 32
        display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

        font_main = bitmap_font.load_font(FONT_PATH)

        text_area_1 = label.Label(font_main, color=0xFFFFFF)
        text_area_1.x =  0
        text_area_1.y = 12

        text_area_2 = label.Label(terminalio.FONT, color=0xFFFFFF)
        text_area_2.x = 10
        text_area_2.y = 28

        text_area_3 = label.Label(terminalio.FONT, color=0xFFFFFF)
        text_area_3.x = 0
        text_area_3.y =  28

        root = displayio.Group()
        display.root_group = root
        root.append(text_area_1)
        root.append(text_area_2)
        root.append(text_area_3)

        self.text_area_1 = text_area_1
        self.text_area_2 = text_area_2
        self.text_area_3 = text_area_3

    def set_text_1(self, text):
        self.text_area_1.text = text
        
    def set_text_2(self, text):
        self.text_area_2.text = text

    def set_text_3(self, text):
        self.text_area_3.text = text

    def blank_screen(self):
        self.set_text_1("")
        self.set_text_2("")
        self.set_text_3("")
        
def test():        
    print(f"\nTesting {__name__}....")
    olo = one_line_oled()
    olo.set_text_1("00:23:34")
    olo.set_text_2("Test-a-roni!")
    olo.set_text_3("X")
    print("Test done.")
    while True:
        pass

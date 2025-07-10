"""
    New display for Practice Monitor
    For 1.44" 128x128 TFT - https://learn.adafruit.com/adafruit-1-44-color-tft-with-micro-sd-socket
    https://www.adafruit.com/product/2088

    Feather     EYESPI
    -------     ------
    SCK         SCK
    MO          MOSI
    MI          MISO
    D5          TCS
    D6          DC
    D9          RST

"""

import random
import time

import board
import displayio

from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_st7735r import ST7735R
from fourwire import FourWire
import terminalio


TEXT_COLOR_ACTIVE   = 0x00_00_00
TEXT_COLOR_INACTIVE = 0xA0_A0_A0


BLACK = 0x000000
BACKGROUND_COLOR = 0x40_40_40
FRAME_COLOR = 0x00_00_FF
BORDER_SIZE = 5

HEIGHT = 128
WIDTH  = 128

class TFT144Display():
    """Display based on Adafruit 1.44" TFT"""

    def __init__(self, pin_cs, pin_dc, pin_reset):
        
        # Important!
        displayio.release_displays()

        spi = board.SPI()

        display_bus = FourWire(spi, command=pin_dc, chip_select=pin_cs, reset=pin_reset)
        display = ST7735R(display_bus, width=WIDTH, height=HEIGHT, colstart=2, rowstart=1)

        # 90 gets us top == side with EYESPI connector.
        display.rotation = 90


        # Make the display context
        splash = displayio.Group()
        display.root_group = splash

        color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
        color_palette = displayio.Palette(1)
        color_palette[0] = FRAME_COLOR

        bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
        splash.append(bg_sprite)

        # # Draw a smaller inner rectangle
        # inner_bitmap = displayio.Bitmap(WIDTH-BORDER_SIZE*2, HEIGHT-BORDER_SIZE*2, 1)
        # inner_palette = displayio.Palette(1)
        # inner_palette[0] = BACKGROUND_COLOR
        # inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=BORDER_SIZE, y=BORDER_SIZE)
        # splash.append(inner_sprite)

        # font_to_use = terminalio.FONT
        font_to_use = bitmap_font.load_font("fonts/cmuntb22.bdf")

        y_height = 20

        # tx = BORDER_SIZE + 2
        tx = 2
        ty = 10
        lab = label.Label(font_to_use, text="Practice", scale=1, color=BLACK, x=tx, y=ty)
        splash.append(lab)
        self._label_1 = lab

        ty += y_height
        text_area = label.Label(font_to_use, text=" 0:00:00", scale=1, color=BLACK,  x=tx, y=ty)
        splash.append(text_area)
        self._text_area_1 = text_area

        ty += y_height + 5
        lab = label.Label(font_to_use, text="Play", scale=1, color=BLACK, x=tx, y=ty)
        splash.append(lab)
        self._label_2 = lab

        ty += y_height
        text_area = label.Label(font_to_use, text=" 0:00:00", scale=1, color=BLACK,  x=tx, y=ty)
        splash.append(text_area)
        self._text_area_2 = text_area

        print("PracMonTFT OK!")


    def set_text_1(self, text):
        self._text_area_1.text = text

    def set_text_1_color(self, color):
        self._text_area_1.color = color

    def set_text_2(self, text):
        self._text_area_2.text = text

    def set_text_2_color(self, color):
        self._text_area_2.color = color

    # label can only change color
    def set_label_1_color(self, color):
        self._label_1.color = color

    def set_label_2_color(self, color):
        self._label_2.color = color

    def set_display_practice_mode(self, practice_mode):

        if practice_mode:
            self.set_label_1_color(TEXT_COLOR_ACTIVE)
            self.set_text_1_color(TEXT_COLOR_ACTIVE)
            self.set_label_2_color(TEXT_COLOR_INACTIVE)
            self.set_text_2_color(TEXT_COLOR_INACTIVE)
        else:
            self.set_label_1_color(TEXT_COLOR_INACTIVE)
            self.set_text_1_color(TEXT_COLOR_INACTIVE)
            self.set_label_2_color(TEXT_COLOR_ACTIVE)
            self.set_text_2_color(TEXT_COLOR_ACTIVE)


print("Creating PracMonTFT....")

disp = TFT144Display(board.D5, board.D6, board.D9)


# disp.set_text_1("1:23:45")
# disp.set_text_2("2:34:56")

# time.sleep(2)
# print("change color")
# disp.set_text_1("9:55:55")
# # disp.set_text_2_color(TEXT_COLOR_INACTIVE)
# # disp.set_label_2_color(TEXT_COLOR_INACTIVE)
# disp.set_display_practice_mode(True)


def increment_time(h, m, s):
    """Return (h,m,s)"""
    s += 1
    if s == 60:
        m += 1
        s = 0
    if m == 60:
        h += 1
        m = 0
    return h, m, s

h_prac = 0
m_prac = 0
s_prac = 0

h_play = 0
m_play = 0
s_play = 0

practice = True
while True:
    disp.set_display_practice_mode(practice)
    r = random.randint(15, 30)
    for i in range(r):
        if practice:
            h_prac, m_prac, s_prac = increment_time(h_prac, m_prac, s_prac)
            disp.set_text_1(f" {h_prac:01}:{m_prac:02}:{s_prac:02}")
        else:
            h_play, m_play, s_play = increment_time(h_play, m_play, s_play)
            disp.set_text_2(f" {h_play:01}:{m_play:02}:{s_play:02}")
        time.sleep(.1)
    practice = not practice


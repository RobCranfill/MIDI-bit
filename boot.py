# boot.py for Practice Montior for Feather
#
# This will be called at startup.

# The default action for CircuitPython is to enter what we call "dev mode", 
# but we want the default to be what we call "run mode".

# If the NVM says to go to dev mode, we are done here.
# If NVM says run mode, give the user a chance to abort that by pressing the BOOT button.

# Either way, flash the LED to show what mode we are going to.

#
# see https://learn.adafruit.com/circuitpython-essentials?view=all#circuitpython-storage
#

import board
import digitalio
import microcontroller
import neopixel
import storage
import time

import midibit_defines as DEF


RUN_MODE_COLOR = (255, 0, 0)
DEV_MODE_COLOR = (0, 255, 0)

BUTTON = board.D7

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

def blink(times, color_triple):
    for i in range(times):
        pixel.fill(color_triple)
        time.sleep(.2)
        pixel.fill((0,0,0))
        time.sleep(.2)


###########################################################################

# Check the NVM state. If set for dev mode, do that.
# Otherwise give the user a chance to force dev mode; if they don't, go to run mode.

go_dev_mode = microcontroller.nvm[0] == DEF.MAGIC_NUMBER_DEV_MODE
print(f"{microcontroller.nvm[0]=} -> {go_dev_mode=}")

if not go_dev_mode:

    # Blink blue 5 times, pause, then read button.
    blink(5, (0, 0, 255))
    time.sleep(1)

    button = digitalio.DigitalInOut(BUTTON)
    button.switch_to_input(pull=digitalio.Pull.UP)
    button_pushed = not button.value
    if button_pushed:
        go_dev_mode = True
        print(f"Button pushed -> {go_dev_mode=}")

    else:
        try:

            # For the second parameter of 'storage.remount()':
            # Pass True to make the CIRCUITPY drive writable by your computer.
            # Pass False to make the CIRCUITPY drive writable by CircuitPython.

            storage.remount("/", False)

        except Exception as e:
            print(f"Failed! ({e})")
            blink(5, (255, 255, 0))
            pixel.fill((255, 255, 0))

# Blink & hold: green if dev mode, red if run mode.
#
if go_dev_mode:
    blink(3, DEV_MODE_COLOR)
    pixel.fill(DEV_MODE_COLOR)
else:
    blink(3, RUN_MODE_COLOR)
    pixel.fill(RUN_MODE_COLOR)

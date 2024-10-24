# boot.py for Practice Montior for Feather
#
# This will be called at startup.
# Blink the NeoPixel blue 5 times, then look at the BOOT button.
#
# If the button is not pushed, we want "run" mode, 
# and will mount the flash in non-USB mode, so we can write to Flash/CIRCUITPY from CircuitPython.
#
# If the button is pushed, we want "dev" mode,
# and we can mount the flash as a writable CIRCUITPY drive, editable from the PC dev environment.
#
# So normally we will run in non-dev mode, so the code can write session data to the flash.

# see https://learn.adafruit.com/circuitpython-essentials?view=all#circuitpython-storage

import board
import digitalio
import json
import neopixel
import storage
import time


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


# At startup, blink blue 5 times, pause, then read button.
blink(5, (0, 0, 255))
time.sleep(1)


# We will use "read/write"", unless the BOOT button is pressed.
button = digitalio.DigitalInOut(BUTTON)
button.switch_to_input(pull=digitalio.Pull.UP)
go_dev_mode = not button.value
print(f"Button -> {go_dev_mode=}")
# print(f"CIRCUITPY {'Unlocked: Dev Mode' if go_dev_mode is True else 'Locked: Run Mode'}")


# For the second parameter of 'storage.remount()':
# Pass True to make the CIRCUITPY drive writable by your computer.
# Pass False to make the CIRCUITPY drive writable by CircuitPython.

try:
    storage.remount("/", go_dev_mode)

    # Blink green if dev mode, red if run mode, yellow if failure to set mode.
    #  (fails if this isn't really boot time, for instance.)
    #
    if go_dev_mode:
        blink(3, DEV_MODE_COLOR)
        pixel.fill(DEV_MODE_COLOR)
    else:
        blink(3, RUN_MODE_COLOR)
        pixel.fill(RUN_MODE_COLOR)

except:
    print("Failed! Can't change mode while developing.")
    blink(3, (255, 255, 0))

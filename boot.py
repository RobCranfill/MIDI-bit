# boot.py for Practice Montior for Feather
#
# This will be called at startup.
# Blink the NeoPixel blue 5 times, then look at the BOOT button.
#
# If the button is not pushed, we are in "run" mode, 
# and will mount the flash in non-USB mode, so we can write to Flash/CIRCUITPY from CircuitPython.
#
# If the button is pushed, we are in "dev" mode,
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


BUTTON = board.D7

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

def blink(times, color_triple):
    for i in range(times):
        pixel.fill(color_triple)
        time.sleep(.1)
        pixel.fill((0,0,0))
        time.sleep(.1)

# At startup, blink blue 5 times, delay, then read button.
blink(5, (0, 0, 255))
time.sleep(1)

# We will use "read/write"", unless the BOOT button is pressed.
button = digitalio.DigitalInOut(BUTTON)
button.switch_to_input(pull=digitalio.Pull.UP)
go_dev_mode = not button.value
# print(f"Button -> {go_dev_mode=}")
print(f"CIRCUITPY {'Unlocked: Dev Mode' if go_dev_mode is True else 'Locked: Run Mode'}")


# For the second parameter of 'storage.remount()':
# Pass True to make the CIRCUITPY drive writable by your computer.
# Pass False to make the CIRCUITPY drive writable by CircuitPython.

try:
    storage.remount("/", go_dev_mode)

    # Blink green if dev mode, red if run mode, yellow if failure to set mode.
    #  (fails if this isn't really boot time, for instance.)
    #
    # time.sleep(2)
    if go_dev_mode:
        blink(4, (0, 255, 0))
    else:
        blink(4, (255, 0, 0))
    # time.sleep(2)

except:
    print("Failed! Can't change mode while developing.")
    blink(2, (255, 255, 0))

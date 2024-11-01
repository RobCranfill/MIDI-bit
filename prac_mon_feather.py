# Practice Monitor for Feather RP2040 Feather with USB Host

# stdlibs
import board
import digitalio
import neopixel
import supervisor
import time
import usb.core

# adafruit libs
import adafruit_datetime as datetime
import adafruit_midi
import adafruit_midi.midi_message

# FIXME: this seems clunky. can't I do this more succinctly?
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend

import adafruit_usb_host_midi

# Our libs
import one_line_oled


MIDI_TIMEOUT = 1.0
SESSION_TIMEOUT = 15
SETTINGS_NAME = "pm_settings.text"


# Read the non-volitile memory for the dev mode set by boot.py.
import microcontroller
_dev_mode = False
if microcontroller.nvm[0:1] == b"\xff":
    _dev_mode = True
print(f"{_dev_mode=}")

_led = digitalio.DigitalInOut(board.LED)
_led.direction = digitalio.Direction.OUTPUT
def flash_led(seconds):
    global _led
    _led.value = True
    time.sleep(seconds)
    _led.value = False


RUN_MODE_COLOR = (128, 0, 0)
DEV_MODE_COLOR = (0, 128, 0)
def set_run_or_dev():
    global SESSION_TIMEOUT
    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
    if _dev_mode:
        pixel.fill(DEV_MODE_COLOR)
        SESSION_TIMEOUT = 5
        print(f"DEV MODE: Setting timeout to {SESSION_TIMEOUT}")
    else:
        pixel.fill(RUN_MODE_COLOR)


SPINNER = "|/-\\"
spinner_index_ = 0
def spin():
    '''Return the next wiggling text characater.'''
    global spinner_index_
    spinner_index_ = (spinner_index_+1) % len(SPINNER)
    return SPINNER[spinner_index_]

def as_hms(seconds):
    return str(datetime.timedelta(0, int(seconds)))

def show_session_time(display, seconds):
    display.set_text_2(f"Session: {as_hms(seconds)}")

def show_total_time(display, seconds):
    display.set_text_1(as_hms(seconds))

def write_session_data(session_seconds):
    '''This will throw an exception if the filesystem isn't writable. Catch it higher up.'''
    print(f"write_session_data: {int(session_seconds)}")
    with open(SETTINGS_NAME, "w") as f:
        f.write(str(int(session_seconds)))

def read_session_data():
    result = "0"
    try:
        with open(SETTINGS_NAME, "r") as f:
            result = f.read()
    except:
        print("No old session data? Continuing....")
    if len(result) == 0:
        result = "0"
    # print(f"read_session_data: returning '{result}'")
    return result

def find_midi_device(display):
    print("Looking for midi devices...")
    display.set_text_2("Looking for MIDI...")
    raw_midi = None
    attempt = 1
    while raw_midi is None:
        all_devices = usb.core.find(find_all=True)
        for device in all_devices:
            try:
                raw_midi = adafruit_usb_host_midi.MIDI(device, timeout=MIDI_TIMEOUT)
                print(f"Found vendor 0x{device.idVendor:04x}, device 0x{device.idProduct:04x}")
                print(f"{device.product=}")
            except ValueError:
                continue

        # FIXME: we always get one extraneous error message
        print(f"No MIDI device found on try #{attempt}. Sleeping....")
        time.sleep(1)
        attempt += 1

    midi_device = adafruit_midi.MIDI(midi_in=raw_midi)
    print(f"Found {device.product}")
    display.set_text_2(f"Found {device.product}")
    return midi_device


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# turn off auto-reload, cuz it's a pain
supervisor.runtime.autoreload = False
print(f"\n*** {supervisor.runtime.autoreload=}\n")

set_run_or_dev()

# Load previous session data from text file.
total_seconds = int(read_session_data())
print(f"read_session_data: {total_seconds=}")

# Update the display
disp = one_line_oled.one_line_oled()

last_event_time = time.monotonic()

in_session = False
session_start_time = 0

# show_session_time(disp, 0)
show_total_time(disp, total_seconds)


idle_start_time = 0
IDLE_TIMEOUT = 10

midi_device = None
while True:
    # print(f"waiting for event; {in_session=}")

    if midi_device is None:
        midi_device = find_midi_device(disp)
    else:
        try:
            msg = midi_device.receive()
        except usb.core.USBError:
            print("usb.core.USBError!")
            midi_device = None
            continue # break?

        event_time = time.monotonic()
        if msg:

            # print(f"midi msg: {msg} @ {event_time:.1f}")
            disp.set_text_2("")
            disp.set_text_3(spin())

            last_event_time = time.monotonic()
            if in_session:
                pass
            else:
                print("\nStarting session")
                session_start_time = time.monotonic()
                in_session = True
        else:
            # print("  empty message")
            pass

        if in_session:
            if event_time - last_event_time > SESSION_TIMEOUT:
                # print("\nTIMEOUT!")
                in_session = False
                # total_seconds += time.monotonic() - session_start_time
                # print(f"  Total session time now {as_hms(total_seconds)}")
                # show_total_time(disp, total_seconds)
                disp.set_text_3(" ")

                total_seconds += session_length
                try:
                    write_session_data(total_seconds)
                    disp.set_text_3("!") # happy write
                except Exception as e:

                    # we expect write errors in dev mode.
                    if _dev_mode:
                        print("Can't write, as expected")
                    else:
                        print(f"Can't write! {e}")

                        # Show an "X" to indicate failed write. FIXME.
                        disp.set_text_3("X")
                        time.sleep(2)
                        disp.set_text_3("")

                # deal with screen timeout
                idle_start_time = time.monotonic()

            else:
                # update current session info
                session_length = time.monotonic() - session_start_time
                # print(f"  Session now {as_hms(session_length)}")
                # show_session_time(disp, session_length)

                # UPDATE ALWAYS?
                show_total_time(disp, total_seconds + session_length)

        else:
            print("  not in session...")
            # pass

            if time.monotonic() - idle_start_time > IDLE_TIMEOUT:
                print("idle timeout!")
                disp.blank_screen()
                flash_led(0.1)


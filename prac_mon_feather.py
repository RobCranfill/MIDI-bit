"""MIDI Practice Monitor

a.k.a. MIDI-bit - A fitbit for your MIDI keyboard

(c)2024 Rob Cranfill

See https://github.com/RobCranfill/MIDI-bit

Version 1 - Minimum Viable Product - Just keeps track of elapsed time spent practicing.

For CircuitPython, on the device known as 
"Adafruit Feather RP2040 with USB Type A Host" (whew!)
(Adafruit Product ID: 5723)

"""

# stdlibs
import adafruit_midi.note_on
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
import midi_state_machine
import midibit_defines as DEF


# TODO: how does this affect responsiveness? buffering? what-all??
MIDI_TIMEOUT = .1

# Defaults will be changed if dev mode
SESSION_TIMEOUT = 15
DISPLAY_IDLE_TIMEOUT = 60 # for display blanking

SETTINGS_NAME = "pm_settings.text"

# Force writing of session data? G G G Eb F F F D
MIDI_TRIGGER_SEQ_PREFIX = (67, 67, 67, 63, 65, 65, 65, 62)
MIDI_TRIGGER_SEQ_RESET  = MIDI_TRIGGER_SEQ_PREFIX + (60,) # middle C

# A state machine to watch for the "force write" sequence.
msm_reset = midi_state_machine.midi_state_machine(MIDI_TRIGGER_SEQ_RESET)


# Read the non-volitile memory for the dev mode set by boot.py.
import microcontroller
_dev_mode = False
if microcontroller.nvm[0] == DEF.MAGIC_NUMBER_DEV_MODE:
    _dev_mode = True
# print(f"{microcontroller.nvm[0]=} -> {_dev_mode=} ({DEF.MAGIC_NUMBER_DEV_MODE=})")

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
    global DISPLAY_IDLE_TIMEOUT
    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
    if _dev_mode:
        pixel.fill(DEV_MODE_COLOR)
        SESSION_TIMEOUT = 5
        DISPLAY_IDLE_TIMEOUT = 10
        print(f"DEV MODE: Setting timeouts to {SESSION_TIMEOUT=}, {DISPLAY_IDLE_TIMEOUT=}\n")
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
    '''Writes a string-ified version of the integer value.
    This will throw an exception if the filesystem isn't writable. Catch it higher up.'''
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
    
    no_midi_idle_start_time = time.monotonic()

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

        # No-MIDI timeout; flass LED twice?
        if time.monotonic() - no_midi_idle_start_time > DISPLAY_IDLE_TIMEOUT:
            # print("no-MIDI idle timeout!")
            display.blank_screen()
            flash_led(0.01)
            time.sleep(0.1)
            flash_led(0.01)

        attempt += 1

    midi_device = adafruit_midi.MIDI(midi_in=raw_midi)
    print(f"Found {device.product}")
    display.set_text_2(f"Found {device.product}")
    time.sleep(2) # FIXME ? arbitrary
    return midi_device


def try_write_session_data(disp, seconds):
    '''Write the given elapsed time to the data file.'''
    global _dev_mode
    try:
        write_session_data(seconds)
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


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# turn off auto-reload, cuz it's a pain
supervisor.runtime.autoreload = False
print(f"{supervisor.runtime.autoreload=}")


set_run_or_dev()

# Load previous total time from text file.
total_seconds = int(read_session_data())
print(f"read_session_data: {total_seconds=}")

# Update the display
disp = one_line_oled.one_line_oled()

last_event_time = time.monotonic()

in_session = False
session_start_time = 0

show_total_time(disp, total_seconds)
last_displayed_time = int(total_seconds)

idle_start_time = time.monotonic()
idle_led_blip_time = idle_start_time

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

            # Assume this is a MIDI disconnect?
            if in_session:
                total_seconds_temp= total_seconds + session_length
                print(f"* Force write: {total_seconds=}, {session_length=}")
                try_write_session_data(disp, total_seconds+session_length)

            midi_device = None
            continue

        event_time = time.monotonic()
        if msg:

            # print(f"midi msg: {msg} @ {event_time:.1f}")
            disp.set_text_2("")
            disp.set_text_3(spin())

            last_event_time = time.monotonic()
            if in_session:
                # pass

                # Also look for command sequences - FIXME: only if in session?
                if isinstance(msg, NoteOn):
                    if msm_reset.note(msg.note):
                        print(f"* Got {MIDI_TRIGGER_SEQ_RESET=}")
                        total_seconds = 0
                        last_displayed_time = 0
                        session_length = 0
                        session_start_time = time.monotonic()
                        show_total_time(disp, total_seconds)

                        try_write_session_data(disp, total_seconds)

                    # if msm_force_write.note(msg.note):
                    #     # don't update total_seconds yet, but write the new value
                    #     total_seconds_temp = total_seconds + session_length
                    #     print(f"* Force write: {total_seconds=}, {total_seconds_temp=}")
                    #     try_write_session_data(disp, total_seconds_temp)

            else:
                print("\nStarting session")
                session_start_time = time.monotonic()
                in_session = True

        else:
            # print("  empty message")
            pass

        if in_session:
            if event_time - last_event_time > SESSION_TIMEOUT:

                # print("\nSESSION_TIMEOUT!")
                in_session = False
                disp.set_text_3(" ")

                total_seconds += session_length

                try_write_session_data(disp, total_seconds)

                # deal with screen timeout
                idle_start_time = time.monotonic()

            else:
                # update current session info
                session_length = time.monotonic() - session_start_time
                # print(f"  Session now {as_hms(session_length)}")

                show_total_time(disp, total_seconds + session_length)

                new_total = total_seconds + session_length
                if last_displayed_time != int(new_total):
                    last_displayed_time = int(new_total)
                    # print(f" updating at {last_displayed_time}")
                    show_total_time(disp, new_total)

        else:
            # print("  not in session...")

            # With-MIDI display timeout
            if time.monotonic() - idle_start_time > DISPLAY_IDLE_TIMEOUT:
                # print("idle timeout!")
                disp.blank_screen()

                # Single flash of LED,only once per second
                if time.monotonic() - idle_led_blip_time > 1:
                    flash_led(0.01)
                    idle_led_blip_time = time.monotonic()


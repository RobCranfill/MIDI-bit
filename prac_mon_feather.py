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
import board
import digitalio
import microcontroller
import neopixel
import supervisor
import time
import usb.core

# adafruit libs
import adafruit_datetime as datetime
import adafruit_midi
import adafruit_midi.midi_message

# FIXME: this seems clunky. can't we do this more succinctly?
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend

import adafruit_usb_host_midi

# Our libs
import two_line_oled
import midi_state_machine
import midibit_defines as DEF


# TODO: how does this affect responsiveness? buffering? what-all??
MIDI_TIMEOUT = .1

# Timeouts, in seconds.
# Defaults will be changed if dev mode
SESSION_TIMEOUT = 15
DISPLAY_IDLE_TIMEOUT = 60 # for display blanking

SETTINGS_NAME = "pm_settings.text"

# Keyboard "attention" sequence MIDI notes: G G G Eb F F F D
MIDI_TRIGGER_SEQ_PREFIX = (67, 67, 67, 63, 65, 65, 65, 62)
MIDI_TRIGGER_SEQ_RESET = MIDI_TRIGGER_SEQ_PREFIX + (60,) # middle C
MIDI_TRIGGER_SEQ_TOGGLE_BOOT = MIDI_TRIGGER_SEQ_PREFIX + (62,) # D above middle C


neopixel_ = neopixel.NeoPixel(board.NEOPIXEL, 1)
def flash_led(seconds):
    neopixel_.fill(flash_color_)
    time.sleep(seconds)
    neopixel_.fill((0,0,0))

def set_run_or_dev():
    '''Set the NeoPixel state and some other globals; return dev mode flag'''

    global SESSION_TIMEOUT
    global DISPLAY_IDLE_TIMEOUT
    global flash_color_

    RUN_MODE_COLOR = (128, 0, 0)
    DEV_MODE_COLOR = (0, 128, 0)
    flash_color_ = RUN_MODE_COLOR

    # Read the non-volatile memory for the dev mode set by boot.py.
    is_dev_mode = False
    if microcontroller.nvm[0] == DEF.MAGIC_NUMBER_DEV_MODE:
        is_dev_mode = True
    # print(f"{microcontroller.nvm[0]=} -> {is_dev_mode=} ({DEF.MAGIC_NUMBER_DEV_MODE=})")

    if is_dev_mode:
        flash_color_ = DEV_MODE_COLOR
        neopixel_.fill(flash_color_)
        SESSION_TIMEOUT = 5
        DISPLAY_IDLE_TIMEOUT = 10
        print(f"DEV MODE: Setting timeouts to {SESSION_TIMEOUT=}, {DISPLAY_IDLE_TIMEOUT=}\n")
    else:
        neopixel_.fill(flash_color_)
    return is_dev_mode

SPINNER = "|/-\\"
spinner_index_ = 0
def spin():
    '''Return the next wiggling text characater.'''
    global spinner_index_
    spinner_index_ = (spinner_index_+1) % len(SPINNER)
    return SPINNER[spinner_index_]

def as_hms(seconds):
    return str(datetime.timedelta(0, int(seconds)))

def show_total_time(disp, seconds):
    disp.set_text_1(as_hms(seconds))

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

def find_midi_device(disp):
    """Does not return until it sees a MIDI device"""

    print("Looking for midi devices...")
    disp.set_text_2("Looking for MIDI...")
    raw_midi = None
    attempt = 1
    
    no_midi_idle_start_time = time.monotonic()

    while raw_midi is None:
        all_devices = usb.core.find(find_all=True)
        for device in all_devices:
            # I guess this is how we find a MIDI device: try it; if not MIDI, will throw exception.
            print(f" looking at device {device=}")
            try:
                raw_midi = adafruit_usb_host_midi.MIDI(device, timeout=MIDI_TIMEOUT)
                print(f"Found vendor 0x{device.idVendor:04x}, device 0x{device.idProduct:04x}")
                print(f"{device.product=}")
                break
            except ValueError:
                continue

        if raw_midi is not None:
            continue

        print(f"No MIDI device found on try #{attempt}. Sleeping....")
        time.sleep(1)

        # No-MIDI timeout; flash LED twice
        if time.monotonic() - no_midi_idle_start_time > DISPLAY_IDLE_TIMEOUT:
            # print("no-MIDI idle timeout!")
            disp.blank_screen()
            flash_led(0.01)
            time.sleep(0.1)
            flash_led(0.01)

        attempt += 1

    midi_device = adafruit_midi.MIDI(midi_in=raw_midi)
    disp.set_text_2(f"Found {device.product}")
    time.sleep(2) # FIXME ? arbitrary
    return midi_device


def try_write_session_data(dev_mode, disp, seconds):
    '''Write the given elapsed time to the data file. Display errors as needed.'''
    try:
        write_session_data(seconds)
        disp.set_text_2("DATA SAVED")
        time.sleep(2)

    except Exception as e:

        # we expect write errors in dev mode.
        if dev_mode:
            print("Can't write, as expected")
            disp.set_text_2("FAILED TO SAVE - OK")
            time.sleep(2)
            disp.set_text_2("")

        else:
            print(f"Can't write! {e}")

            disp.set_text_2("FAILED TO SAVE!")
            time.sleep(2)
            disp.set_text_2("")


def toggle_boot_mode(disp):
    nvm_dev_mode = microcontroller.nvm[0] == DEF.MAGIC_NUMBER_DEV_MODE
    nvm_dev_mode = not nvm_dev_mode
    microcontroller.nvm[0] = DEF.MAGIC_NUMBER_DEV_MODE if nvm_dev_mode else DEF.MAGIC_NUMBER_RUN_MODE
    print(f"Setting {microcontroller.nvm[0]=}")
    disp.set_text_2(f"Dev: {nvm_dev_mode}")
    time.sleep(2)
    disp.set_text_2("")


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# turn off auto-reload, cuz it's a pain
supervisor.runtime.autoreload = False
print(f"{supervisor.runtime.autoreload=}")

# Are we running in dev mode? Set some stuff.
in_dev_mode = set_run_or_dev()

# Load previous total time from text file.
total_seconds = int(read_session_data())
print(f"read_session_data: {total_seconds=}")

# The display.
display = two_line_oled.two_line_oled()

last_event_time = time.monotonic()

in_session = False
session_start_time = 0

show_total_time(display, total_seconds)
last_displayed_time = int(total_seconds)

idle_start_time = time.monotonic()
idle_led_blip_time = idle_start_time

# A state machine to watch for the "reset" sequence.
msm_reset = midi_state_machine.midi_state_machine(MIDI_TRIGGER_SEQ_RESET)

# A state machine to watch for the "toggle boot mode" sequence.
msm_toggle_boot = midi_state_machine.midi_state_machine(MIDI_TRIGGER_SEQ_TOGGLE_BOOT)


midi_device = None
while True:
    # print(f"waiting for event; {in_session=}")

    if midi_device is None:
        midi_device = find_midi_device(display)

    # TODO: remove this as 'else' to fix one-off error?
    else:
        try:
            msg = midi_device.receive()
        except usb.core.USBError:
            print("usb.core.USBError!")

            # Assume this is a MIDI disconnect?
            if in_session:
                total_seconds_temp = total_seconds + session_length
                print(f"* Force write: {total_seconds=}, {session_length=}")
                try_write_session_data(in_dev_mode, display, total_seconds+session_length)

            midi_device = None
            continue

        event_time = time.monotonic()
        if msg:

            # print(f"midi msg: {msg} @ {event_time:.1f}")
            display.set_text_2(spin())

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
                        show_total_time(display, total_seconds)

                        try_write_session_data(in_dev_mode, display, total_seconds)

                    elif msm_toggle_boot.note(msg.note):
                        print(f"* Got {MIDI_TRIGGER_SEQ_TOGGLE_BOOT=}")
                        toggle_boot_mode(display)

                    # if msm_force_write.note(msg.note):
                    #     # don't update total_seconds yet, but write the new value
                    #     total_seconds_temp = total_seconds + session_length
                    #     print(f"* Force write: {total_seconds=}, {total_seconds_temp=}")
                    #     try_write_session_data(display, total_seconds_temp)

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
                display.set_text_2("")

                total_seconds += session_length

                try_write_session_data(in_dev_mode, display, total_seconds)

                # deal with screen timeout
                idle_start_time = time.monotonic()

            else:
                # update current session info
                session_length = time.monotonic() - session_start_time
                # print(f"  Session now {as_hms(session_length)}")

                show_total_time(display, total_seconds + session_length)

                new_total = total_seconds + session_length
                if last_displayed_time != int(new_total):
                    last_displayed_time = int(new_total)
                    # print(f" updating at {last_displayed_time}")
                    show_total_time(display, new_total)

        else:
            # print("  not in session...")

            # With-MIDI display timeout
            if time.monotonic() - idle_start_time > DISPLAY_IDLE_TIMEOUT:
                # print("idle timeout!")
                display.blank_screen()

                # Single flash of LED, once per second.
                if time.monotonic() - idle_led_blip_time > 1:
                    flash_led(0.01)
                    idle_led_blip_time = time.monotonic()


"""MIDI Practice Monitor

a.k.a. MIDI-bit - A fitbit for your MIDI keyboard

(c)2024 Rob Cranfill

See https://github.com/RobCranfill/MIDI-bit

Version 1 - Minimum Viable Product - Just keeps track of elapsed time spent practicing.

For CircuitPython, on the device known as 
"Adafruit Feather RP2040 with USB Type A Host" (whew!)
(Adafruit Product ID: 5723)

To force startup mode,

import microcontroller
microcontroller.nvm[0] = 0x12 # for run
microcontroller.nvm[0] = 0x34 # for dev

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
MIDI_TRIGGER_SEQ_TEST = MIDI_TRIGGER_SEQ_PREFIX + (64,) # E


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
        print(f"\nDEV MODE: Setting timeouts to {SESSION_TIMEOUT=}, {DISPLAY_IDLE_TIMEOUT=}\n")
    else:
        neopixel_.fill(flash_color_)
        print(f"\nRUN MODE")
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
    """Does not return until it finds a MIDI device"""

    print("Looking for MIDI devices in USB...")
    display_message_for_a_bit(disp, "Looking for MIDI", delay=1)
    raw_midi = None
    attempt = 1
    
    no_midi_idle_start_time = time.monotonic()

    while raw_midi is None:
        all_devices = usb.core.find(find_all=True)
        for device in all_devices:
            print(f" - looking at USB device vendor 0x{device.idVendor:04x}, product 0x{device.idProduct:04x}") # FIXME: this is not useful

            # I guess this is how we find a MIDI device: try it; if not MIDI, will throw exception.
            try:
                raw_midi = adafruit_usb_host_midi.MIDI(device, timeout=MIDI_TIMEOUT)
                print(f" ^ MIDI OK for device {device.product=}")
                break
            except ValueError:
                print(" ValueError?")
                continue

        # Looked at all devices, didn't find MIDI. Try again.
        if raw_midi is None:

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
    time.sleep(2)

    return midi_device


def try_write_session_data(dev_mode, disp, seconds):
    '''Write the given elapsed time to the data file. Display errors as needed.'''
    try:
        write_session_data(seconds)
        display_message_for_a_bit(disp, "DATA SAVED")

    except Exception as e:

        # we expect write errors in dev mode.
        if dev_mode:
            print("Can't write, as expected")
            display_message_for_a_bit(disp, "FAILED TO SAVE - OK")

        else:
            print(f"Can't write! {e}")
            display_message_for_a_bit(disp, "FAILED TO SAVE!")


def toggle_boot_mode(disp):
    nvm_dev_mode = microcontroller.nvm[0] == DEF.MAGIC_NUMBER_DEV_MODE
    nvm_dev_mode = not nvm_dev_mode
    microcontroller.nvm[0] = DEF.MAGIC_NUMBER_DEV_MODE if nvm_dev_mode else DEF.MAGIC_NUMBER_RUN_MODE
    print(f"Setting {microcontroller.nvm[0]=} -> {nvm_dev_mode=}")
    display_message_for_a_bit(disp, f"Dev: {nvm_dev_mode}")

def display_message_for_a_bit(disp, text, delay=2):
    disp.set_text_2(str(text))
    time.sleep(delay)
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
# FIXME: Why is the I2C addr different???
display = two_line_oled.two_line_oled(0x3d, 64)

last_event_time = time.monotonic()

in_session = False
session_start_time = 0

show_total_time(display, total_seconds)

# last_displayed_time is the (integer) time we last displayed; only update if changed.
# (The time itself is a float that's always changing.)
# 
last_displayed_time = int(total_seconds)

idle_start_time = time.monotonic()
idle_led_blip_time = idle_start_time

# A state machine to watch for the "reset" sequence.
msm_reset = midi_state_machine.midi_state_machine(MIDI_TRIGGER_SEQ_RESET)

# A state machine to watch for the "toggle boot mode" sequence.
msm_toggle_boot = midi_state_machine.midi_state_machine(MIDI_TRIGGER_SEQ_TOGGLE_BOOT)

# For testing shit
# msm_test = midi_state_machine.midi_state_machine(MIDI_TRIGGER_SEQ_TEST)

# Main event loop. Does not exit.
#
midi_device = None
while True:

    # This doesn't return until we have a MIDI device.
    # TODO: Is it always a *usable* device?
    #
    if midi_device is None:
        print("MEL loking for MIDI....")
        midi_device = find_midi_device(display)

    # print(f"waiting for event; {in_session=}")
    # TODO: remove this as 'else' to fix one-off error?
    # else:

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

    # TODO: Should we only pay attention to NoteOn events?

    if msg:
        last_event_time = time.monotonic()

        print(f"\nmidi msg: {msg} @ {event_time:.1f}")
        display.set_text_2(spin())

        if not in_session:
            print("\nStarting session")
            session_start_time = time.monotonic()
            in_session = True

            # This would only be missing for <1 sec, but hey.
            show_total_time(display, total_seconds)

        # Look for command sequences.
        if isinstance(msg, NoteOn):

            # Could be a zero-velofiy "note off".
            if msg.velocity == 0:
                # print("note off!")
                continue

            if msm_reset.note(msg.note):
                print(f"* Got {MIDI_TRIGGER_SEQ_RESET=}")
                total_seconds = 0
                last_displayed_time = 0
                session_length = 0
                session_start_time = time.monotonic()
                show_total_time(display, total_seconds)

                try_write_session_data(in_dev_mode, display, total_seconds)

            if msm_toggle_boot.note(msg.note):
                print(f"* Got {MIDI_TRIGGER_SEQ_TOGGLE_BOOT=}")
                toggle_boot_mode(display)

            # if msm_test.note(msg.note):
            #     print(f"ENTER TEST MODE {msg.note=}")

            # if msm_force_write.note(msg.note):
            #     # don't update total_seconds yet, but write the new value
            #     total_seconds_temp = total_seconds + session_length
            #     print(f"* Force write: {total_seconds=}, {total_seconds_temp=}")
            #     try_write_session_data(display, total_seconds_temp)

    # else:
    #     # print("  empty message")
    #     pass

    # We have handled the event/note. Now do other stuff.
    #
    if in_session:

        # Session timeout?
        if event_time - last_event_time > SESSION_TIMEOUT:

            # print("\nSESSION_TIMEOUT!")
            in_session = False
            display.set_text_2("")

            total_seconds += session_length

            try_write_session_data(in_dev_mode, display, total_seconds)

            # For idle screen timeout
            idle_start_time = time.monotonic()

        else:
            # Update current session info
            session_length = time.monotonic() - session_start_time
            # print(f"  Session now {as_hms(session_length)}")

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


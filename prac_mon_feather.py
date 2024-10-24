# Practice Monitor for Feather RP2040 Feather with USB Host

import adafruit_datetime as datetime
import adafruit_midi
import adafruit_midi.midi_message

import adafruit_usb_host_midi

# TODO: how can i import all these so I don't get 'MIDIUnknownEvent'?
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.control_change import ControlChange

import board
import neopixel
import usb_midi

import usb.core
import supervisor
import time

import two_line_oled


SETTINGS_NAME = "pm_settings.text"

SPINNER = "|/-\\"
spinner_index_ = 0

MIDI_TIMEOUT = 1.0
SESSION_TIMEOUT = 5


RUN_MODE_COLOR = (255, 0, 0)
DEV_MODE_COLOR = (0, 255, 0)
def set_led_to_run_or_dev():
    print(f"{is_filesystem_writeable()=}")
    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
    if is_filesystem_writeable():
        pixel.fill(RUN_MODE_COLOR)
    else:
        pixel.fill(DEV_MODE_COLOR)


def is_filesystem_writeable():
    result = True
    try:
        with open("testfile.foo", "w") as f:
            f.write()
            f.close()
    except:
        result = False
    return result


# display a little wiggling text characater.
def spin():
    global spinner_index_
    spinner_index_ = (spinner_index_+1) % len(SPINNER)
    return SPINNER[spinner_index_]

def as_hms(seconds):
    return str(datetime.timedelta(0, int(seconds)))

def show_session_time(display, seconds):
    display.set_text_2(f"Session: {as_hms(seconds)}")

def show_total_session_time(display, seconds):
    display.set_text_1(as_hms(seconds))

def write_session_data(data_str):
    with open(SETTINGS_NAME, "w") as f:
        f.write(data_str)
        # f.close()

def read_session_data():
    result = "0"
    try:
        with open(SETTINGS_NAME, "r") as f:
            result = f.read()
            # f.close()
    except:
        print("No old session data? Continuing....")
    
    if len(result) == 0:
        result = "0"

    print(f"read_session_data: returning '{result}'")
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

        # FIXME: we get one extraneous error message
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


# doesn't work 
# set_led_to_run_or_dev()


# Load previous session data from text file.
old_session_time = int(read_session_data())
print(f"{old_session_time=}")

# Update the display
disp = two_line_oled.two_line_oled()


last_event_time = time.monotonic()

in_session = False
session_start_time = 0
session_total_time = old_session_time

show_session_time(disp, 0)
show_total_session_time(disp, session_total_time)

midi_device = None
while True:
    # print(f"waiting for event; {in_session=}")

    if midi_device is None:
        midi_device = find_midi_device(disp)
    else:
        try:
            msg = midi_device.receive()
        except usb.core.USBError:
            print("down!")
            midi_device = None
            continue # break?
        
        event_time = time.monotonic()
        if msg:

            # print(f"midi msg: {msg} @ {event_time:.1f}")

            # disp.set_text_3(spin())

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
            if  event_time - last_event_time > SESSION_TIMEOUT:
                # print("\nTIMEOUT!")
                in_session = False
                session_total_time += time.monotonic() - session_start_time
                print(f"  Total session time now {as_hms(session_total_time)}")
                show_total_session_time(disp, session_total_time)

                try:
                    write_session_data(str(int(session_total_time)))
                except Exception as e:
                    print(f"Can't write! {e}")

            else:
                # update current session info
                session_length = time.monotonic() - session_start_time
                # print(f"  Session now {as_hms(session_length)}")
                show_session_time(disp, session_length)

        else:
            pass
            # print("  not in session...")

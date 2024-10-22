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

import usb.core
import supervisor
import time

import oled_display

SETTINGS_NAME = "pm_settings.text"

SPINNER = "|/-\\"
spinner_index_ = 0

MIDI_TIMEOUT = 1.0
SESSION_TIMEOUT = 5


def spin():
    global spinner_index_
    spinner_index_ = (spinner_index_+1) % len(SPINNER)
    return SPINNER[spinner_index_]

def as_hms(seconds):
    return str(datetime.timedelta(0, int(seconds)))

def show_session_time(display, seconds):
    display.set_text_1(f"Session: {as_hms(seconds)}")

def show_total_session_time(display, seconds):
    display.set_text_2(f"  Total: {as_hms(seconds)}")

def write_session_data(data_str):
    with open(SETTINGS_NAME, "w") as f:
        f.write(data_str)
        f.close()

def read_session_data():
    result = 0
    try:
        with open(SETTINGS_NAME, "r") as f:
            result = f.read()
            f.close()
    except:
        print("No old session data? Continuing....")
    return result

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# turn off auto-reload, cuz it's a pain
supervisor.runtime.autoreload = False
print(f"\n*** {supervisor.runtime.autoreload=}\n")


old_session_time = int(read_session_data())
print(f"{old_session_time=}")


disp = oled_display.oled_display()
disp.set_text_1("Looking for MIDI...")

print("Looking for midi devices...")
raw_midi = None
while raw_midi is None:
    all_devices = usb.core.find(find_all=True)
    # print(f"{all_devices=}")
    for device in all_devices:
        try:
            raw_midi = adafruit_usb_host_midi.MIDI(device, timeout=MIDI_TIMEOUT)
            print(f"Found vendor 0x{device.idVendor:04x}, device 0x{device.idProduct:04x}")
        except ValueError:
            print("No MIDI (or USB) device found. Sleeping....")
            time.sleep(1)
            continue

midi_device = adafruit_midi.MIDI(midi_in=raw_midi)
disp.set_text_1("MIDI OK!")

last_event_time = time.monotonic()

in_session = False
session_start_time = 0
session_total_time = old_session_time


while True:
    # print(f"waiting for event; {in_session=}")
    msg = midi_device.receive()
    event_time = time.monotonic()
    if msg:
        print(f"midi msg: {msg} @ {event_time:.1f}")
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
        if  event_time - last_event_time > SESSION_TIMEOUT:
            # print("\nTIMEOUT!")
            in_session = False
            session_total_time += time.monotonic() - session_start_time
            print(f"  Total session time now {as_hms(session_total_time)}")
            show_total_session_time(disp, session_total_time)
        else:
            # update current session info
            session_length = time.monotonic() - session_start_time
            print(f"  Session now {as_hms(session_length)}")
            show_session_time(disp, session_length)


    else:
        pass
        # print("  not in session...")

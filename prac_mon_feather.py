import adafruit_midi
import adafruit_midi.midi_message

# TODO: how can i import all these so I don't get 'MIDIUnknownEvent'?
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.control_change import ControlChange

import adafruit_usb_host_midi
import usb.core
import time

import supervisor
supervisor.runtime.autoreload = False  # CirPy 8 and above
print(f"\n*** {supervisor.runtime.autoreload=}\n")


MIDI_TIMEOUT = 1.0

# seconds - ok? 
SESSION_TIMEOUT = 5


print("Looking for midi devices...")
raw_midi = None
while raw_midi is None:
    for device in usb.core.find(find_all=True):
        try:
            raw_midi = adafruit_usb_host_midi.MIDI(device, timeout=MIDI_TIMEOUT)
            print(f"Found vendor 0x{device.idVendor:04x}, device 0x{device.idProduct:04x}")
        except ValueError:
            print("No MIDI (or USB) device found. Sleeping....")
            time.sleep(1)
            continue

midi_device = adafruit_midi.MIDI(midi_in=raw_midi, in_channel=0)


last_event_time = time.monotonic()

in_session = False
session_start_time = 0
session_total_time = 0

while True:
    print(f"waiting for event; {in_session=}")
    msg = midi_device.receive()
    event_time = time.monotonic()
    if msg:
        print(f"midi msg: {msg} @ {event_time}")
        last_event_time = time.monotonic()
        if in_session:
            pass
        else:
            print("\nStarting session!")
            session_start_time = time.monotonic()
        in_session = True
    else:
        print("  empty message")

    if in_session:
        if  event_time - last_event_time > SESSION_TIMEOUT:
            print("\nTIMEOUT!")
            in_session = False
            session_total_time += time.monotonic() - session_start_time
            print(f"  Total session time now {session_total_time}")
        else:
            # show current session info
            print(f"  Session now {time.monotonic() - session_start_time} seconds")

    else:
        pass
        # print("  not in session...")

# Practice Monitor for Feather RP2040 Feather with USB Host

# test of using MIDI notes as a trigger

# stdlibs
import board
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


MIDI_TIMEOUT = 0.1

def find_midi_device():
    print("Looking for midi devices...")
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
    return midi_device


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# turn off auto-reload, cuz it's a pain
supervisor.runtime.autoreload = False
print(f"\n*** {supervisor.runtime.autoreload=}\n")

msg_count = 0

TRIGGER_NOTE = 56

import midi_state_machine
msm = midi_state_machine.midi_state_machine((60, 62, 64))


midi_device = None
while True:

    if midi_device is None:
        midi_device = find_midi_device()
    else:
        # print(f"waiting for event with {MIDI_TIMEOUT} second timeout")
        try:
            midi_msg = midi_device.receive()
        except usb.core.USBError:
            print("usb.core.USBError!")
            midi_device = None
            continue

        if midi_msg:
            event_time = time.monotonic()
            msg_count += 1
            print(f"midi msg #{msg_count}: {midi_msg} @ {event_time:.1f}")

            if isinstance(midi_msg, NoteOn):
                note = midi_msg.note
                # print(f" {note=}")
                if msm.note(note):
                    print("\nSEQUENCE DETECTED!\n")

        else:
            # print("  empty message")
            pass



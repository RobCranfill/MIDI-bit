# A simplified (no UART output) version of 
#   examples/usb_host_midi_simpletest_rp2040usbfeather.py

# SPDX-FileCopyrightText: Copyright (c) 2023 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
# pylint: disable=unused-import

import board
import busio
import usb.core
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange
from adafruit_midi.pitch_bend import PitchBend
import adafruit_usb_host_midi

import time # cran

print("Looking for midi device") # cran
raw_midi = None
while raw_midi is None:

    one_device = usb.core.find(idVendor=0x1718)
    print(f"idVendor=0x1718 -> {one_device=}")
    one_device = usb.core.find(idVendor=0x0499)
    print(f"idVendor=0x0499 -> {one_device=}")

    devices = usb.core.find(find_all=True)
    print(f"{devices=}; iterating....") # cran
    for device in devices:
        try:
            raw_midi = adafruit_usb_host_midi.MIDI(device)
            print("Found", hex(device.idVendor), hex(device.idProduct))
        except ValueError:
            print(f"ValueError!")
            continue
    print(f"{raw_midi=}; sleeping.....") # cran
    time.sleep(1) # cran

# output not needed for this demo/test
# # This setup is to use TX pin on Feather RP2040 with USB Type A Host as MIDI out
# # You must wire up the needed resistors and jack yourself
# # This will forward all MIDI messages from the device to hardware uart MIDI
# uart = busio.UART(rx=board.RX, tx=board.TX, baudrate=31250, timeout=0.001)

midi_device = adafruit_midi.MIDI(midi_in=raw_midi, in_channel=0)
# midi_uart = adafruit_midi.MIDI(midi_out=uart, midi_in=uart)


while True:
    msg = midi_device.receive()
    if msg:
        print("midi msg:", msg)
        # midi_uart.send(msg)


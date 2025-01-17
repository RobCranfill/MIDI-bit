#!/bin/bash
# prep to push

cp -v $CP/README.md .
cp -v $CP/boot.py .
cp -v $CP/prac_mon_feather.py .
cp -v $CP/midibit_defines.py .
cp -v $CP/oled_display.py .
cp -v $CP/one_line_oled.py .
cp -v $CP/two_line_oled.py .
cp -v $CP/midi_state_machine.py .

git status


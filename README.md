# pracMonFeather
MIDI Practice Monitor for a Feather Microcontroller

&copy;2024 Rob Cranfill

# Purpose
Elevator Pitch: A FitBit for MIDI keyboards. Tells you how much you have practiced via various metrics.

# Design Goals
Something that plugs into the USB port of a MIDI keyboard; no external power requirement would be nice.

# Hardware Requirements for this project
* Adafruit "RP2040 with USB A Host" (Adafruit part number 5723)
* Adafruit 0.91" OLED Display (P/N 4440)
  * REPLACE WITH SOMETHING NICER/BIGGER, LATER
* Power supply - wall wart or lithium battery?
  * Going to need to be plugged in, either to wall or USB power from keyboard.
* Use the BOOT button for user input.
  * Is just one button enough?

# Software Requirements

* CircuitPython
  * 9.1.4 used so far.
* Adafruit support libraries
  * See requirements.txt for complete list and latest versions used.
* Font: fonts/LeagueSpartan-Bold-16.bdf

# Open Issues
* What data to preserve?
  * Just total practice time? Is "session" time useful?
* Without some kind of networking, how can we ever export data?
* Show Run/Dev mode via NeoPixel, all the time?
  * If set in boot.py, state doesn't survive into code.py !?

# Closed Issues
  * How to preserve data across restarts?
  * Write to a file, I assume. When? How often?
    * Write to a file when session ends.

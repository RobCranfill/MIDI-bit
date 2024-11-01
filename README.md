# MIDI-bit
MIDI Practice Monitor
&copy;2024 Rob Cranfill

# Purpose
Elevator Pitch: A Fitbit for MIDI keyboards. Tells you how much you have practiced via various metrics.

# Design Goals
Something that plugs into the USB port of a MIDI keyboard, with auto start/stop, so you can forget about it.

Minimum Viable Product: Accumulate total practice time for a given interval.

Stretch goals: Internet connectivity, with an app to slice and dice the data.

# Operation
* Plug it in to MIDI & USB power (or LiPo for Feather)
* NeoPixel will blink blue 5 times; you have 2 seconds to press the BOOT button to put it into "dev mode" (see below).
* Play the keyboard and watch your time accumulate!


# Hardware Requirements for this project
* Adafruit "RP2040 with USB A Host" (Adafruit part number 5723)
* Adafruit 0.91" OLED Display (P/N 4440)
  * TODO: Replace with something bigger, color?
* Power supply - wall wart or lithium battery?
  * Going to need to be plugged in, either to wall or USB power from keyboard.
  *  TODO: Power from Roland USB A port seems problematic.
* Use the BOOT button for user input.
  * Is just one button enough?


# Software Requirements
* CircuitPython
  * 9.2.0 used currently.
* Adafruit support libraries
  * See requirements.txt for complete list and latest versions used.
* Font: 22-point bitmap of FreeType-CMU Typewriter Text-Bold-R-Normal, rendered from OpenType font "cmuntb.ttf", converted by Andrey V. Panov from TeX fonts.


# Open Issues
* How to reset/restart data?
* What data to preserve?
  * Just total practice time? Is "session" time useful? Keypresses??
* Without some kind of networking, how can we ever export data?
* Show Run/Dev mode via NeoPixel, all the time?
  * If set in boot.py, state doesn't survive into code.py !?


# Closed Issues

   * <strike>How to preserve data across restarts?
   * Write to a file, I assume. When? How often?
      * Write to a file when session ends.</strike>

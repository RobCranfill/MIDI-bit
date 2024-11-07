# MIDI-bit
MIDI Practice Monitor
&copy;2024 Rob Cranfill

# Purpose
Elevator Pitch: A Fitbit for MIDI keyboards. Tells you how much you have practiced via various metrics.

# Design Goals
Something that plugs into the USB port of a MIDI keyboard, with auto start/stop, so you can forget about it.

Minimum Viable Product: Accumulate total practice time until reset.

Stretch goals: Internet connectivity, with an app to slice and dice the data all pretty-like.

# Operation
* Plug it in to MIDI & USB power (Feather can run on battery but is that practical?)
* Play the keyboard and watch your time accumulate!
* If no MIDI is connected, or no MIDI events are detected in the timeout period (60 seconds in RUN mode, 10 seconds in DEV mode (see below)) the screen will be blanked and the red LED will blink once per second (3 blinks per second if no MIDI, just for now).
* Keyboard control sequences
  * In order to send commands to the unit from the MIDI keyboard, instead of using MIDI CC or PC commands, which some keyboards may not accomodate, you can play the first eight notes of Beethoven's 5th, starting on G above middle C, to get the unit's attentions.
    * That's G G G Eb F F F D; the tempo doesn't matter.
    * After the attention sequence, 
      * Middle C: Zero out session data (and write it to storage).
      * Unimplemented/not useful? <strike>D above middle C: Write session data immediately.</strike>

* RUN/DEV MODE
  * For now, there are these two modes. Useful for development, but ultimately not needed?
  * At boot (running 'boot.py'), the code will blink the NeoPixel blue 5 times, then wait 2 seconds; 
  if at the end of that period the BOOT button is being pressed we will enter DEV MODE, 
  otherwise it's RUN MODE.
  * boot.py will set the Feather's flash memory to "READ ONLY" if in DEV MODE.
  See [adafruit.com](https://learn.adafruit.com/circuitpython-essentials/circuitpython-storage) for more info.
  * This means in RUN MODE, the default, the CircuitPython code can write to the flash, and can update the accumulated practice time.
    In DEV MODE, we can edit the files on the flash drive via the USB C connector, and update the code - but the running code cannot update the stored practice time.
    This is OK since that would be just garbage, 'testing' numbers anyway.
  * Once we start running 'code'.py', if RUN MODE we set the NeoPixel to red (Red == Run), 
  otherwise set it to green.

# Hardware Requirements for this project
* Adafruit "RP2040 with USB A Host" (Adafruit part number 5723)
* Adafruit 0.91" OLED Display (P/N 4440)
  * TODO: Replace with something bigger, color?
* Power supply - wall wart or lipo battery?
  * Going to need to be plugged in, either to wall or USB power from keyboard.
  *  TODO: Power from Roland USB A port seems problematic. Why?
* Use the BOOT button for user input?
  * Is just one button enough? No; used keyboard sequences.


# Software Requirements
* CircuitPython
  * 9.2.0 used currently.
* Adafruit support libraries
  * See requirements.txt for complete list and latest versions used.
* Font: 22-point bitmap of FreeType-CMU Typewriter Text-Bold-R-Normal, rendered from OpenType font "cmuntb.ttf", converted by Andrey V. Panov from TeX fonts.


# Open Issues (also see GitHub)
* What data to preserve?
  * Just total practice time? Is "session" time useful? Keypresses??
* Without some kind of networking, how can we ever export data?

# Closed Issues
* How to reset/restart data?
* How to preserve data across restarts?
   * Write to a file, I assume. When? How often?
      * Write to a file when session ends.
* Show Run/Dev mode via NeoPixel, all the time.
  * If set in boot.py, state doesn't survive into code.py


"""MIDI-bit - A fitbit for your MIDI keyboard.
 Version 2, with larger LED display and practice/play time.

(c)2025 Rob Cranfill

See https://github.com/RobCranfill/MIDI-bit

Version 1 - Minimum Viable Product - Just keeps track of elapsed time spent practicing.
Version 2 - Add practice/play mode.

For CircuitPython, on the device known as 
"Adafruit Feather RP2040 with USB Type A Host" (whew!)
(Adafruit Product ID: 5723)

To force startup mode,
    import microcontroller
    microcontroller.nvm[0] = 0x12 # for run
  or
    microcontroller.nvm[0] = 0x34 # for dev

"""

# stdlibs
import time

import board
import microcontroller
import neopixel
import supervisor
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

# Which display are we using?
# import one_line_oled
# import two_line_oled
import tft_144_display

PIN_TFT_CS = board.D5
PIN_TFT_DC = board.D6
PIN_TFT_RESET = board.D9

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
# MIDI_TRIGGER_SEQ_TEST = MIDI_TRIGGER_SEQ_PREFIX + (64,) # E
MIDI_TRIGGER_SEQ_TOGGLE_PRAC_PLAY = MIDI_TRIGGER_SEQ_PREFIX + (65,) # F


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

def show_total_time(disp, prac_seconds, play_seconds):
    """Display the practice and play totals."""
    disp.set_text_1(as_hms(prac_seconds))
    disp.set_text_2(as_hms(play_seconds))

def write_session_data(practice_seconds, play_seconds):
    '''Write a string-ified version of the integer value.
    This will throw an exception if the filesystem isn't writable. Catch it higher up.'''

    print(f"write_session_data: {int(practice_seconds)=}, {int(play_seconds)=}")
    with open(SETTINGS_NAME, "w") as f:
        f.write(str(int(practice_seconds)) + "\n")
        f.write(str(int(play_seconds)))


def read_session_data():
    """Return old (practice,play) values."""

    try:
        with open(SETTINGS_NAME, "r") as f:
            r1 = f.readline()
            r2 = f.readline()
    except:
        print("No old session data? Continuing....")

    if len(r1) == 0:
        practice = 0
    else:
        practice = int(r1.strip())
    play = int(r2)

    print(f"read_session_data: returning ({practice=}, {play=})")
    return practice, play

def find_midi_device(disp):
    """Does not return until it finds a (suitable?) MIDI device"""

    # does this help weird startup behavior? No,
    # time.sleep(1)

    print("\nLooking for MIDI devices...")

    # display_message_for_a_bit(disp, "Looking for MIDI", delay=1)
    disp.set_text_status("Looking for MIDI....")

    raw_midi = None
    attempt = 1
    
    no_midi_idle_start_time = time.monotonic()

    while raw_midi is None:
        all_devices = usb.core.find(find_all=True)
        
        #  no can do 
        # print(f"  Found {len(all_devices)} devices?")

        for device in all_devices:
            
            # FIXME: this is not useful?
            print(f" - looking at USB device vendor 0x{device.idVendor:04x}, product 0x{device.idProduct:04x}") 

            # I guess this is how we find a MIDI device: try it; if not MIDI, will throw exception.
            try:
                raw_midi = adafruit_usb_host_midi.MIDI(device, timeout=MIDI_TIMEOUT)
                print(f" ^ MIDI OK for {device.product=}")
                if device.product is None:
                    print("FUNNY DEVICE; SKIPPING!")
                    continue
                else:
                   break

            except ValueError:
                print(" * adafruit_usb_host_midi.MIDI: ValueError?")
                continue
            except Exception as e:
                    print(f" * adafruit_usb_host_midi.MIDI: {e}")

        print(f"  Done iterating MIDI devices, found {raw_midi}")

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

    try:
        midi_device = adafruit_midi.MIDI(midi_in=raw_midi)
    except Exception as e:
        print(f" * adafruit_midi.MIDI: {e}")

    print(f"  returning {midi_device=}")
    disp.set_text_status(f"Found {raw_midi}")
    return midi_device


def try_write_session_data(dev_mode, disp, prac, play):
    '''Write the given elapsed time to the data file. Display errors as needed.'''
    try:
        write_session_data(prac, play)
        display_message_for_a_bit(disp, "DATA SAVED")

    except Exception as e:

        # we expect write errors in dev mode.
        if dev_mode:
            print("Can't write, as expected in dev mode.")
            display_message_for_a_bit(disp, "FAILED TO SAVE - OK", delay=5)
        else:
            print(f"Can't write! {e}")
            display_message_for_a_bit(disp, "FAILED TO SAVE!", delay=5)


def toggle_boot_mode(disp):
    nvm_dev_mode = microcontroller.nvm[0] == DEF.MAGIC_NUMBER_DEV_MODE
    nvm_dev_mode = not nvm_dev_mode
    microcontroller.nvm[0] = DEF.MAGIC_NUMBER_DEV_MODE if nvm_dev_mode else DEF.MAGIC_NUMBER_RUN_MODE
    print(f"Setting {microcontroller.nvm[0]=} -> {nvm_dev_mode=}")
    display_message_for_a_bit(disp, f"Dev: {nvm_dev_mode}")

def display_message_for_a_bit(disp, text, delay=2):
    disp.set_text_status(str(text))
    time.sleep(delay)
    disp.set_text_status("")



# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

def main():

    # NEW: are we in 'practice' mode, as opposed to 'play' mode?
    practice_not_play_mode = True

    # turn off auto-reload, cuz it's a pain
    supervisor.runtime.autoreload = False
    print(f"{supervisor.runtime.autoreload=}")

    # Are we running in dev mode? Set some stuff.
    in_dev_mode = set_run_or_dev()

    # Load previous total time from text file.
    total_seconds_prac, total_seconds_play = read_session_data()
    print(f"read_session_data: {total_seconds_prac=}, {total_seconds_play=}")


    # The display.
    # FIXME: exeption?
    display = None
    display = tft_144_display.TFT144Display(PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RESET)
    print("Created TFT display")
    if display == None:
        print("Can't init display??")
        return

    # display.set_text_status("This still yet another test that should wrap.")
    # time.sleep(4)

    display.set_display_practice_mode(practice_not_play_mode)
    

    last_event_time = time.monotonic()
    in_session = False
    session_start_time = 0

    show_total_time(display, total_seconds_prac, total_seconds_play)

    # last_displayed_time is the (integer) time we last displayed; only update if changed.
    # (The time itself is a float that's always changing.)
    # 
    last_displayed_time_prac = int(total_seconds_prac)
    last_displayed_time_play = int(total_seconds_play)

    idle_start_time = time.monotonic()
    idle_led_blip_time = idle_start_time

    # A state machine to watch for the "reset" sequence.
    msm_reset = midi_state_machine.midi_state_machine(MIDI_TRIGGER_SEQ_RESET)

    # A state machine to watch for the "toggle boot mode" sequence.
    msm_toggle_boot = midi_state_machine.midi_state_machine(MIDI_TRIGGER_SEQ_TOGGLE_BOOT)

    # State machine to catch command to toggle practice/play mode.
    msm_toggle_practice_play = midi_state_machine.midi_state_machine(MIDI_TRIGGER_SEQ_TOGGLE_PRAC_PLAY)

    # # For testing stuff
    # msm_test = midi_state_machine.midi_state_machine(MIDI_TRIGGER_SEQ_TEST)

    # wait for USB ready??? nah
    # time.sleep(2) 

    # Main event loop. Does not exit.
    #
    midi_device = None
    msg_number = 0
    while True:

        # This doesn't return until we have a MIDI device.
        # TODO: Is it always a *usable* device? No. Something funny here.
        #
        if midi_device is None:

            print("MEL loking for MIDI....")

            # Wait for a MIDI device....
            midi_device = find_midi_device(display)
            print("  back from find_midi_device")

            # TODO: check for None?
            # stop screen timeout immediately after finding ?
            last_event_time = time.monotonic()

        # print(f"waiting for event; {in_session=}")
        # TODO: remove this as 'else' to fix one-off error?
        # else:

        try:
            msg = midi_device.receive()
        except usb.core.USBError as e:
            print(f" ** midi_device.receive: usb.core.USBError: '{e}'")

            # Assume this is a MIDI disconnect?
            if in_session:
                total_seconds_temp = total_seconds_prac + session_length
                print(f"* Force write: {total_seconds_prac=}, {session_length=}")
                try_write_session_data(in_dev_mode, display, total_seconds_prac+session_length)

                # TODO: end the session?

            last_event_time = time.monotonic()

            midi_device = None
            continue

        event_time = time.monotonic()

        # Got MIDI?
        if msg:
            msg_number += 1

            # We only act on MIDI "NoteOn" messages.
            if not isinstance(msg, NoteOn):
                # print(f"Not a MIDI ON message! ({msg_number})")
                # print(f"  > midi msg: {msg} @ {event_time:.1f}")
                continue

            # print(f"midi msg: {msg} @ {event_time:.1f}")

            last_event_time = time.monotonic()

            display.set_text_status(spin())

            if not in_session:
                print("\nStarting session")
                session_start_time = time.monotonic()
                in_session = True

                # This would only be missing for <1 sec, but hey.
                show_total_time(display, total_seconds_prac, total_seconds_play)

            # Look for command sequences.
            if isinstance(msg, NoteOn):

                # Could be a zero-velocity NoteOn which is really a "note off".
                if msg.velocity == 0:
                    # print("note off!")
                    continue

                # Is it a MIDI state machine command?
                #
                if msm_reset.note(msg.note):
                    print("* Got MIDI_TRIGGER_SEQ_RESET")
                    total_seconds_prac = 0
                    total_seconds_play = 0
                    last_displayed_time_prac = 0
                    last_displayed_time_play = 0
                    session_length = 0
                    session_start_time = time.monotonic()
                    show_total_time(display, total_seconds_prac, total_seconds_play)

                    try_write_session_data(in_dev_mode, display, total_seconds_prac, total_seconds_play)

                elif msm_toggle_boot.note(msg.note):
                    print("* Got MIDI_TRIGGER_SEQ_TOGGLE_BOOT")
                    toggle_boot_mode(display)

                elif msm_toggle_practice_play.note(msg.note):
                    print("* Got MIDI_TRIGGER_SEQ_TOGGLE_PRAC_PLAY!")

                    # TODO: this ends the previous prac/play session; need to start a new one
                    # FIXME: WHEN DOES OLD SESSION END??? HOW DO WE DIVIDE UP THE PRAC/PLAY TIME????

                    print(f" * MIDI escape start - {msm_toggle_practice_play.get_seq_start_time()=}")

                    print(f" - before adjust {total_seconds_prac=}, {total_seconds_play=}")

                    time_to_subtract = time.monotonic() - msm_toggle_practice_play.get_seq_start_time()
                    print(f" - offset {} by {time_to_subtract=}")
                    if practice_not_play_mode:
                        total_seconds_prac -= time_to_subtract
                    else:
                        total_seconds_play -= time_to_subtract

                    print(f" - after adjust {total_seconds_prac=}, {total_seconds_play=}")

                    practice_not_play_mode = not practice_not_play_mode

                    show_total_time(display, total_seconds_prac, total_seconds_play)
                    display.set_display_practice_mode(practice_not_play_mode)
 

                # elif msm_force_write.note(msg.note):
                #     # don't update total_seconds_prac yet, but write the new value
                #     total_seconds_temp = total_seconds_prac + session_length
                #     print(f"* Force write: {total_seconds_prac=}, {total_seconds_temp=}")
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
                display.set_text_status("")

                if practice_not_play_mode:
                    total_seconds_prac += session_length
                else:
                    total_seconds_play += session_length

                try_write_session_data(in_dev_mode, display, total_seconds_prac, total_seconds_play)

                # For idle screen timeout
                idle_start_time = time.monotonic()

            else:
                # Update current session info
                session_length = time.monotonic() - session_start_time
                # print(f"  Session now {as_hms(session_length)}")

                if practice_not_play_mode:
                    new_total = total_seconds_prac + session_length
                    if last_displayed_time_prac != int(new_total):
                        last_displayed_time_prac = int(new_total)
                        # print(f" updating at {last_displayed_time_prac=}")
                else:
                    new_total = total_seconds_play + session_length
                    if last_displayed_time_play != int(new_total):
                        last_displayed_time_play = int(new_total)
                        # print(f" updating at {last_displayed_time_play=}")
                show_total_time(display, last_displayed_time_prac, last_displayed_time_play)

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


# Run the code!
main()


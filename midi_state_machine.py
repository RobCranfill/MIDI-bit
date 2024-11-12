'''
A state machine to watch for a particular sequence of notes.
Create the class, giving it the sequence being watched for;
call 'note()' method with each new note;
if the sequence is completed, note() will return true.
'''

class midi_state_machine:

    def __init__(self, note_list, debug=False):
        """
        note_list is a tuple of the MIDI notes that will constitue a "hit".
        This only handles one sequence; if you want more triggers, create more state machines.
        """

        self.note_list_ = note_list
        self.debug_ = debug

        # this is the index of the last in-sequence item we got; -1 if none
        self.last_hit_ = -1

        self.debug_print(f"MSM: {note_list=}")


    def debug_print(self, str):
        if self.debug_:
            print(str)

    def note(self, new_note):
        """Return true iff this new note completes the sequence."""

        self.debug_print(f"Testing {new_note=}; {self.last_hit_=}")

        if new_note != self.note_list_[self.last_hit_ + 1]:
            self.debug_print("  Next is NOT in sequence")

            # But what if it's FIRST in the sequence?
            if new_note == self.note_list_[0]:
                self.debug_print("  But it IS first in sequence")
                self.last_hit_ = 0
                return False

            self.last_hit_ = -1
            return False

        self.last_hit_ += 1
        self.debug_print(f"  Note is a hit! Now at index {self.last_hit_} of target")

        if self.last_hit_ < len(self.note_list_) - 1:
            self.debug_print(f"  Not at end of list yet ")
            return False

        self.debug_print(" ^^^ Complete!")
        self.last_hit_ = -1
        return True


def test():

    msm = midi_state_machine((3, 4, 5))

    test = msm.note(1)
    test = msm.note(2)

    test = msm.note(3)
    test = msm.note(4)
    test = msm.note(5)

    test = msm.note(6)
    test = msm.note(4)
    test = msm.note(3)

    test = msm.note(3)
    test = msm.note(4)
    test = msm.note(5)

    test = msm.note(1)
    test = msm.note(2)


# test()

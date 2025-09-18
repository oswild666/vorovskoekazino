import time
from collections import deque
import numpy as np

# Standard MIDI clock pulses per quarter note (PPQN)
PPQN = 24

class Track:
    """Represents a single track in a pattern."""
    def __init__(self, name: str, midi_channel: int, steps: int = 16):
        self.name = name
        self.midi_channel = midi_channel
        self.length = steps
        self.steps = [False] * steps # True for active, False for inactive

    def toggle_step(self, step_index: int):
        """Toggles the state of a single step."""
        if 0 <= step_index < self.length:
            self.steps[step_index] = not self.steps[step_index]

class Pattern:
    """A collection of tracks."""
    def __init__(self, name: str):
        self.name = name
        self.tracks = []

    def add_track(self, track: Track):
        self.tracks.append(track)

class Sequencer:
    """
    The main sequencer engine. Manages state, BPM, and synchronization.
    """
    def __init__(self):
        self.state = 'STOPPED'
        self.trigger_source = 'INIT' # Can be 'MIDI' or 'USER' or 'INIT'
        self.sync_transport = True # If True, responds to MIDI Start/Stop/Continue
        self.bpm_source = 'EXTERNAL' # 'EXTERNAL' or 'INTERNAL'

        # For external BPM calculation
        self._clock_times = deque(maxlen=PPQN)
        self.bpm = 0.0

        # For internal clock control
        self.internal_bpm = 120.0

        # For pattern and step sequencing
        self.patterns = []
        self.current_pattern_index = 0
        self.current_step = 0
        self._last_tick_time = 0.0
        self._create_default_pattern()

    def handle_clock(self):
        """
        Processes a single MIDI clock tick. Calculates BPM using a median filter
        for jitter reduction.
        """
        if self.bpm_source != 'EXTERNAL' or self.state != 'PLAYING':
            return

        current_time = time.monotonic()
        self._clock_times.append(current_time)

        if len(self._clock_times) < 3:
            return

        deltas = np.diff(self._clock_times)
        median_delta = np.median(deltas)

        if median_delta > 0:
            self.bpm = 60.0 / (median_delta * PPQN)

    def start(self, source='USER'):
        """Handles a 'start' event."""
        if source == 'MIDI' and not self.sync_transport:
            return
        print(f"Sequencer: Received START from {source}.")
        if self.bpm_source == 'EXTERNAL':
            self._clock_times.clear()
        self.state = 'PLAYING'
        self.trigger_source = source
        self.current_step = -1 # So the first tick will be step 0
        self._last_tick_time = 0

    def stop(self, source='USER'):
        """Handles a 'stop' event."""
        if source == 'MIDI' and not self.sync_transport:
            return
        print(f"Sequencer: Received STOP from {source}.")
        self.state = 'STOPPED'
        self.trigger_source = source
        if self.bpm_source == 'EXTERNAL':
            self.bpm = 0.0

    def continue_playing(self, source='USER'):
        """Handles a 'continue' event."""
        if source == 'MIDI' and not self.sync_transport:
            return
        print(f"Sequencer: Received CONTINUE from {source}.")
        self.state = 'PLAYING'
        self.trigger_source = source

    def get_current_bpm(self):
        """Returns the active BPM based on the current sync mode."""
        return self.internal_bpm if self.bpm_source == 'INTERNAL' else self.bpm

    def get_status_dict(self):
        """Returns a dictionary with the current status for the TUI."""
        return {
            "state": self.state,
            "bpm_source": self.bpm_source,
            "sync_transport": self.sync_transport,
            "bpm": self.get_current_bpm(),
            "trigger_source": self.trigger_source,
            "current_step": self.current_step,
            "pattern": self.get_current_pattern(),
        }

    def _create_default_pattern(self):
        """Creates a default pattern with a few tracks."""
        pattern1 = Pattern("Default Pattern")
        pattern1.add_track(Track("Kick", 0, 16))
        pattern1.add_track(Track("Snare", 1, 16))
        pattern1.add_track(Track("Hi-Hat", 2, 8)) # Polyrhythm!
        pattern1.add_track(Track("Bass", 3, 12))   # Another polyrhythm!
        self.patterns.append(pattern1)

    def get_current_pattern(self):
        """Returns the currently active pattern, or None."""
        if not self.patterns:
            return None
        return self.patterns[self.current_pattern_index]

    def tick(self, time: float) -> None:
        """
        The sequencer's heartbeat. Called by the TUI's update loop.
        Advances the step based on the current BPM.
        """
        if self.state != 'PLAYING':
            return

        bpm = self.get_current_bpm()
        if bpm == 0:
            return

        # 24 PPQN (MIDI standard) means 24 ticks per quarter note.
        # We'll advance the step every 24 ticks.
        # For now, let's simplify and assume 1 tick per step for demonstration.
        # A more robust implementation would use a proper timing model.

        # Calculate time per step
        seconds_per_beat = 60.0 / bpm
        seconds_per_16th_note = seconds_per_beat / 4 # Our resolution is 16th notes

        if time - self._last_tick_time >= seconds_per_16th_note:
            self._last_tick_time = time

            pattern = self.get_current_pattern()
            if not pattern:
                return

            # Advance step and check for active notes
            # This is a simplified model. A real implementation would be more complex.
            max_len = max(t.length for t in pattern.tracks) if pattern.tracks else 16
            self.current_step = (self.current_step + 1) % max_len

            for track in pattern.tracks:
                step_index = self.current_step % track.length
                if track.steps[step_index]:
                    print(f"Beat! Pattern: {pattern.name}, Track: {track.name}, Step: {step_index}")

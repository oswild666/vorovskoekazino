import time
from collections import deque
import numpy as np

# Standard MIDI clock pulses per quarter note (PPQN)
PPQN = 24

class Sequencer:
    """
    The main sequencer engine. Manages state, BPM, and synchronization.
    """
    def __init__(self):
        self.state = 'STOPPED'
        self.trigger_source = 'INIT' # Can be 'MIDI' or 'USER' or 'INIT'
        self.use_internal_bpm = False # If True, ignores incoming MIDI clock

        # For external BPM calculation
        self._clock_times = deque(maxlen=PPQN)
        self.bpm = 0.0

        # For internal clock control
        self.internal_bpm = 120.0

    def handle_clock(self):
        """
        Processes a single MIDI clock tick. Calculates BPM using a median filter
        for jitter reduction.
        """
        if self.use_internal_bpm or self.state != 'PLAYING':
            return

        current_time = time.monotonic()
        self._clock_times.append(current_time)

        if len(self._clock_times) < 3:
            return

        deltas = np.diff(self._clock_times)
        median_delta = np.median(deltas)

        if median_delta > 0:
            self.bpm = 60.0 / (median_delta * PPQN)

    def start(self, source='MIDI'):
        """Handles a 'start' event from either MIDI or the UI."""
        print(f"Sequencer: Received START from {source}.")
        if not self.use_internal_bpm:
            self._clock_times.clear()
        self.state = 'PLAYING'
        self.trigger_source = source

    def stop(self, source='MIDI'):
        """Handles a 'stop' event from either MIDI or the UI."""
        print(f"Sequencer: Received STOP from {source}.")
        self.state = 'STOPPED'
        self.trigger_source = source
        if not self.use_internal_bpm:
            self.bpm = 0.0

    def continue_playing(self, source='MIDI'):
        """Handles a 'continue' event from either MIDI or the UI."""
        print(f"Sequencer: Received CONTINUE from {source}.")
        self.state = 'PLAYING'
        self.trigger_source = source

    def get_current_bpm(self):
        """Returns the active BPM based on the current sync mode."""
        return self.internal_bpm if self.use_internal_bpm else self.bpm

    def get_status_dict(self):
        """Returns a dictionary with the current status for the TUI."""
        sync_mode_str = "INTERNAL" if self.use_internal_bpm else "EXTERNAL"
        return {
            "state": self.state,
            "sync_mode": sync_mode_str,
            "bpm": self.get_current_bpm(),
            "trigger_source": self.trigger_source
        }

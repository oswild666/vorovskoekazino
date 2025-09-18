import time
from collections import deque
import numpy as np

# Standard MIDI clock pulses per quarter note (PPQN)
PPQN = 24

# Define synchronization modes as constants for clarity and to avoid typos
SYNC_MODES = [
    'EXTERNAL',                      # External BPM and Transport
    'INTERNAL',                      # Internal BPM and Transport
    'INTERNAL_BPM_EXTERNAL_TRANSPORT' # Internal BPM, External Transport
]

class Sequencer:
    """
    The main sequencer engine. Manages state, BPM, and synchronization.
    """
    def __init__(self):
        self.state = 'STOPPED'
        self.sync_mode = SYNC_MODES[0]  # Default to EXTERNAL

        # For external BPM calculation
        self._clock_times = deque(maxlen=PPQN) # Store timestamps of last 24 clock pulses
        self.bpm = 0.0

        # For internal clock control
        self.internal_bpm = 120.0

    def set_sync_mode(self, mode_index):
        """Sets the sync mode by its index in the SYNC_MODES list."""
        if 0 <= mode_index < len(SYNC_MODES):
            self.sync_mode = SYNC_MODES[mode_index]
            print(f"Sequencer: Sync mode set to {self.sync_mode}")
            # Reset state when changing modes
            self.state = 'STOPPED'
            self.bpm = 0.0
            self._clock_times.clear()
        else:
            print(f"Warning: Invalid sync mode index {mode_index}")

    def handle_clock(self):
        """
        Processes a single MIDI clock tick. Calculates BPM using a median filter
        for jitter reduction.
        """
        if self.sync_mode != 'EXTERNAL' or self.state != 'PLAYING':
            return

        current_time = time.monotonic()
        self._clock_times.append(current_time)

        # Need at least a few data points to calculate a meaningful median
        if len(self._clock_times) < 3:
            return

        # Calculate the time differences between consecutive clock ticks
        deltas = np.diff(self._clock_times)

        # Use the median of the deltas to get a jitter-resistant interval
        median_delta = np.median(deltas)

        if median_delta > 0:
            # Formula: BPM = 60 seconds / (time per quarter note)
            # Time per quarter note = (median time per clock tick) * (ticks per quarter note)
            self.bpm = 60.0 / (median_delta * PPQN)

    def start(self):
        """
        Handles a MIDI 'start' message. Resets clock and starts playing.
        """
        if self.sync_mode in ['EXTERNAL', 'INTERNAL_BPM_EXTERNAL_TRANSPORT']:
            print(f"Sequencer: Received START in {self.sync_mode} mode.")
            if self.sync_mode == 'EXTERNAL':
                self._clock_times.clear()
            self.state = 'PLAYING'

    def stop(self):
        """
        Handles a MIDI 'stop' message. Stops playback.
        """
        if self.sync_mode in ['EXTERNAL', 'INTERNAL_BPM_EXTERNAL_TRANSPORT']:
            print(f"Sequencer: Received STOP in {self.sync_mode} mode.")
            self.state = 'STOPPED'
            if self.sync_mode == 'EXTERNAL':
                self.bpm = 0.0  # Reset external BPM when stopped

    def continue_playing(self):
        """
        Handles a MIDI 'continue' message. Resumes playback.
        """
        if self.sync_mode in ['EXTERNAL', 'INTERNAL_BPM_EXTERNAL_TRANSPORT']:
            print(f"Sequencer: Received CONTINUE in {self.sync_mode} mode.")
            self.state = 'PLAYING'

    def get_current_bpm(self):
        """Returns the active BPM based on the current sync mode."""
        if self.sync_mode == 'EXTERNAL':
            return self.bpm
        return self.internal_bpm

    def get_status_dict(self):
        """Returns a dictionary with the current status for the TUI."""
        return {
            "state": self.state,
            "sync_mode": self.sync_mode,
            "bpm": self.get_current_bpm()
        }

# This block allows for standalone testing of the sequencer's logic.
if __name__ == '__main__':
    print("--- Sequencer Logic Test ---")
    seq = Sequencer()

    print(f"Initial Status: {seq.get_status_dict()}")

    # --- Test External Sync Logic ---
    print("\n--- Testing External Sync (Median Filter) ---")
    seq.start()
    print(f"After START: {seq.get_status_dict()}")

    target_bpm = 120.0
    interval = (60.0 / target_bpm) / PPQN
    print(f"Simulating {PPQN-1} clock ticks at {target_bpm} BPM...")

    # Simulate some jitter
    jitter = interval * 0.5
    for i in range(PPQN - 1):
        seq.handle_clock()
        # Add jitter to every 3rd tick
        sleep_interval = interval + jitter if i % 3 == 0 else interval
        time.sleep(sleep_interval)

    print(f"After {PPQN-1} clocks with jitter: {seq.get_status_dict()}")
    print("Note: The median filter should effectively ignore the jitter.")

    seq.stop()
    print(f"After STOP: {seq.get_status_dict()}")

    # --- Test New Sync Mode ---
    print("\n--- Testing Internal BPM / External Transport ---")
    seq.set_sync_mode(2) # INTERNAL_BPM_EXTERNAL_TRANSPORT
    seq.internal_bpm = 140.0
    print(f"Mode set: {seq.get_status_dict()}")
    seq.start()
    print(f"After START: {seq.get_status_dict()}")
    # Tick should be ignored
    seq.handle_clock()
    print(f"After clock tick (should be ignored): {seq.get_status_dict()}")
    seq.stop()
    print(f"After STOP: {seq.get_status_dict()}")

    print("\n--- Test Finished ---")

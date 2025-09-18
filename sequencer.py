import time
from collections import deque

# Standard MIDI clock pulses per quarter note (PPQN)
PPQN = 24

class Sequencer:
    """
    The main sequencer engine. Manages state, BPM, and synchronization.
    """
    def __init__(self):
        self.state = 'STOPPED'  # Can be 'STOPPED' or 'PLAYING'
        self.sync_mode = 'EXTERNAL'  # Can be 'EXTERNAL' or 'INTERNAL'

        # For external BPM calculation
        # A deque provides an efficient, fixed-size queue for our moving average calculation.
        self._clock_times = deque(maxlen=PPQN + 1)
        self.bpm = 0.0

        # For internal clock control
        self.internal_bpm = 120.0
        # Note: The logic for generating an internal clock will be added later.

    def handle_clock(self):
        """
        Processes a single MIDI clock tick. Called by the MidiHandler.
        This method calculates the BPM based on the time between clock ticks.
        """
        if self.sync_mode != 'EXTERNAL' or self.state != 'PLAYING':
            return

        current_time = time.monotonic()
        self._clock_times.append(current_time)

        # We need at least two clock ticks to calculate the first interval.
        if len(self._clock_times) < 2:
            return

        # Calculate the average time delta over the stored clock times.
        # This creates a moving average, which smooths out BPM fluctuations (jitter).
        total_time_span = self._clock_times[-1] - self._clock_times[0]
        num_intervals = len(self._clock_times) - 1

        if num_intervals > 0:
            avg_delta = total_time_span / num_intervals
            # Formula: BPM = 60 seconds / (time per quarter note)
            # Time per quarter note = (average time per clock tick) * (ticks per quarter note)
            if avg_delta > 0:
                self.bpm = 60.0 / (avg_delta * PPQN)

    def start(self):
        """
        Handles a MIDI 'start' message.
        Resets the clock buffer and sets the state to 'PLAYING'.
        """
        if self.sync_mode == 'EXTERNAL':
            print("Sequencer: Received START signal.")
            self._clock_times.clear()
            self.state = 'PLAYING'

    def stop(self):
        """
        Handles a MIDI 'stop' message.
        Stops playback and resets BPM.
        """
        if self.sync_mode == 'EXTERNAL':
            print("Sequencer: Received STOP signal.")
            self.state = 'STOPPED'
            self.bpm = 0.0  # Reset BPM when stopped

    def continue_playing(self):
        """
        Handles a MIDI 'continue' message.
        Resumes playback without resetting the clock.
        """
        if self.sync_mode == 'EXTERNAL':
            print("Sequencer: Received CONTINUE signal.")
            self.state = 'PLAYING'

    def get_status(self):
        """
        Returns a formatted string of the sequencer's current status.
        """
        mode = self.sync_mode.capitalize()
        current_bpm = self.internal_bpm if self.sync_mode == 'INTERNAL' else self.bpm
        return f"State: {self.state} | Mode: {mode} | BPM: {current_bpm:.2f}"

# This block allows for standalone testing of the sequencer's logic.
if __name__ == '__main__':
    print("--- Sequencer Logic Test ---")
    seq = Sequencer()

    print(f"Initial Status: {seq.get_status()}")

    # --- Test External Sync Logic ---
    print("\n--- Testing External Sync ---")
    seq.start()
    print(f"After START: {seq.get_status()}")

    # Simulate receiving clock pulses for 120 BPM
    # 120 BPM = 2 beats/sec => 1 beat = 0.5s
    # Time per MIDI clock tick = 0.5s / 24 PPQN = ~0.02083s
    interval_120_bpm = (60.0 / 120.0) / PPQN
    print(f"Simulating {PPQN} clock ticks at 120 BPM (interval: {interval_120_bpm * 1000:.2f} ms)...")

    for i in range(PPQN):
        # In a real scenario, handle_clock would be called from another thread.
        # Here we just call it directly.
        seq.handle_clock()
        print(f"Tick {i+1:2d}: {seq.get_status()}", end='\r')
        time.sleep(interval_120_bpm)

    # One final clock to make the deque full
    seq.handle_clock()
    print(f"\nAfter {PPQN + 1} clocks: {seq.get_status()}")

    seq.stop()
    print(f"After STOP: {seq.get_status()}")

    # --- Test Internal Sync Mode ---
    print("\n--- Testing Internal Sync ---")
    seq.sync_mode = 'INTERNAL'
    seq.internal_bpm = 140.0
    seq.state = 'PLAYING'  # In internal mode, state is controlled manually
    print(f"Internal Mode Status: {seq.get_status()}")

    print("\n--- Test Finished ---")

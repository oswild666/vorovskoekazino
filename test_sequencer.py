import unittest
from unittest.mock import patch
from sequencer import Sequencer, PPQN

class TestSequencer(unittest.TestCase):

    def setUp(self):
        """Set up a new Sequencer instance before each test."""
        self.sequencer = Sequencer()

    def test_initial_state(self):
        """Test that the sequencer initializes with correct default values."""
        self.assertEqual(self.sequencer.state, 'STOPPED')
        self.assertEqual(self.sequencer.sync_mode, 'EXTERNAL')
        self.assertEqual(self.sequencer.bpm, 0.0)
        self.assertEqual(self.sequencer.internal_bpm, 120.0)

    def test_transport_controls(self):
        """Test the state changes from transport control methods."""
        # Test start
        self.sequencer.start()
        self.assertEqual(self.sequencer.state, 'PLAYING')

        # Test stop
        self.sequencer.state = 'PLAYING'
        self.sequencer.bpm = 120.0
        self.sequencer.stop()
        self.assertEqual(self.sequencer.state, 'STOPPED')
        self.assertEqual(self.sequencer.bpm, 0.0)

        # Test continue
        self.sequencer.state = 'STOPPED'
        self.sequencer.continue_playing()
        self.assertEqual(self.sequencer.state, 'PLAYING')

    @patch('sequencer.time.monotonic')
    def test_bpm_calculation_is_deterministic(self, mock_monotonic):
        """
        Test the BPM calculation with a mocked time source to ensure it is
        deterministic and accurate.
        """
        target_bpm = 150.0
        # The exact time interval between MIDI clock ticks for the target BPM.
        interval = (60.0 / target_bpm) / PPQN

        # Simulate time passing by controlling the return value of time.monotonic()
        mock_time = 0
        mock_monotonic.return_value = mock_time

        self.sequencer.start()

        # Simulate a stream of clock ticks with perfect timing.
        for _ in range(PPQN + 1):
            # Set the "current time" for the handle_clock method.
            mock_monotonic.return_value = mock_time
            self.sequencer.handle_clock()
            # Advance our simulated time by the perfect interval.
            mock_time += interval

        # With a perfect time source, the BPM should be extremely close to the target.
        self.assertAlmostEqual(self.sequencer.bpm, target_bpm, places=5)

    def test_clock_handling_in_stopped_state(self):
        """Test that clock ticks are ignored when the sequencer is stopped."""
        self.sequencer.state = 'STOPPED'
        initial_bpm = self.sequencer.bpm
        self.sequencer.handle_clock()
        self.assertEqual(self.sequencer.bpm, initial_bpm)
        self.assertEqual(len(self.sequencer._clock_times), 0)

    def test_clock_handling_in_internal_mode(self):
        """Test that clock ticks are ignored when in internal sync mode."""
        self.sequencer.sync_mode = 'INTERNAL'
        self.sequencer.state = 'PLAYING'
        initial_bpm = self.sequencer.bpm
        self.sequencer.handle_clock()
        self.assertEqual(self.sequencer.bpm, initial_bpm)
        self.assertEqual(len(self.sequencer._clock_times), 0)

if __name__ == '__main__':
    unittest.main()

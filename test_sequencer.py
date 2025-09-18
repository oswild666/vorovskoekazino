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
        self.assertEqual(self.sequencer.bpm_source, 'EXTERNAL')
        self.assertTrue(self.sequencer.sync_transport)
        self.assertEqual(self.sequencer.bpm, 0.0)
        self.assertEqual(self.sequencer.internal_bpm, 120.0)
        self.assertEqual(self.sequencer.trigger_source, 'INIT')
        self.assertIsNotNone(self.sequencer.get_current_pattern())
        self.assertEqual(len(self.sequencer.get_current_pattern().tracks), 4)

    def test_transport_controls_and_source(self):
        """Test the state changes and trigger source tracking."""
        # Test start from USER
        self.sequencer.start(source='USER')
        self.assertEqual(self.sequencer.state, 'PLAYING')
        self.assertEqual(self.sequencer.trigger_source, 'USER')

        # Test stop from MIDI
        self.sequencer.stop(source='MIDI')
        self.assertEqual(self.sequencer.state, 'STOPPED')
        self.assertEqual(self.sequencer.trigger_source, 'MIDI')

        # BPM should reset when external
        self.sequencer.bpm_source = 'EXTERNAL'
        self.sequencer.bpm = 150.0
        self.sequencer.stop(source='USER')
        self.assertEqual(self.sequencer.bpm, 0.0)

    @patch('sequencer.time.monotonic')
    def test_bpm_calculation_with_median_filter(self, mock_monotonic):
        """
        Test that the median filter for BPM calculation correctly handles jitter.
        """
        self.sequencer.bpm_source = 'EXTERNAL'
        self.sequencer.start(source='MIDI')

        target_bpm = 150.0
        interval = (60.0 / target_bpm) / PPQN

        mock_time = 0
        mock_monotonic.return_value = mock_time

        intervals = [interval] * PPQN
        intervals[5] = interval * 3 # Jitter
        intervals[15] = interval * 0.5 # Jitter

        for i in range(PPQN):
            mock_monotonic.return_value = mock_time
            self.sequencer.handle_clock()
            mock_time += intervals[i]

        self.assertAlmostEqual(self.sequencer.bpm, target_bpm, places=5)

    def test_clock_handling_in_internal_mode(self):
        """Test that clock ticks are ignored when bpm_source is 'INTERNAL'."""
        self.sequencer.bpm_source = 'INTERNAL'
        self.sequencer.state = 'PLAYING'
        initial_bpm = self.sequencer.bpm

        # This should be ignored
        self.sequencer.handle_clock()

        self.assertEqual(self.sequencer.bpm, initial_bpm)
        self.assertEqual(len(self.sequencer._clock_times), 0)
        self.assertEqual(self.sequencer.get_current_bpm(), self.sequencer.internal_bpm)

    def test_transport_sync_toggle(self):
        """Test that MIDI start/stop can be ignored."""
        self.sequencer.sync_transport = False
        self.sequencer.start(source='MIDI')
        self.assertEqual(self.sequencer.state, 'STOPPED') # Should not have started

        self.sequencer.state = 'PLAYING'
        self.sequencer.stop(source='MIDI')
        self.assertEqual(self.sequencer.state, 'PLAYING') # Should not have stopped

if __name__ == '__main__':
    unittest.main()

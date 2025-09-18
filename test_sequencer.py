import unittest
from unittest.mock import patch
from sequencer import Sequencer, PPQN, SYNC_MODES

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

    def test_set_sync_mode(self):
        """Test the set_sync_mode method."""
        # Test setting a valid mode
        self.sequencer.set_sync_mode(1) # INTERNAL
        self.assertEqual(self.sequencer.sync_mode, 'INTERNAL')
        # It should also reset the state
        self.sequencer.state = 'PLAYING'
        self.sequencer.set_sync_mode(2)
        self.assertEqual(self.sequencer.sync_mode, 'INTERNAL_BPM_EXTERNAL_TRANSPORT')
        self.assertEqual(self.sequencer.state, 'STOPPED')

        # Test setting an invalid mode
        initial_mode = self.sequencer.sync_mode
        self.sequencer.set_sync_mode(99) # Invalid index
        self.assertEqual(self.sequencer.sync_mode, initial_mode)

    def test_transport_controls_in_external_mode(self):
        """Test transport controls in EXTERNAL mode."""
        self.sequencer.set_sync_mode(0) # EXTERNAL
        self.sequencer.start()
        self.assertEqual(self.sequencer.state, 'PLAYING')
        self.sequencer.stop()
        self.assertEqual(self.sequencer.state, 'STOPPED')
        self.sequencer.continue_playing()
        self.assertEqual(self.sequencer.state, 'PLAYING')

    @patch('sequencer.time.monotonic')
    def test_bpm_calculation_with_median_filter(self, mock_monotonic):
        """
        Test that the median filter for BPM calculation correctly handles jitter.
        """
        target_bpm = 150.0
        interval = (60.0 / target_bpm) / PPQN

        mock_time = 0
        mock_monotonic.return_value = mock_time
        self.sequencer.start()

        # Simulate a stream of clock ticks with some jitter
        intervals = [interval] * PPQN
        # Introduce a large jitter outlier
        intervals[5] = interval * 3
        intervals[15] = interval * 0.5

        for i in range(PPQN):
            mock_monotonic.return_value = mock_time
            self.sequencer.handle_clock()
            mock_time += intervals[i]

        # The median filter should ignore the outliers and result in a BPM
        # very close to the one calculated from the standard interval.
        self.assertAlmostEqual(self.sequencer.bpm, target_bpm, places=5)

    def test_internal_bpm_external_transport_mode(self):
        """Test the behavior of the 'internal BPM, external transport' mode."""
        self.sequencer.set_sync_mode(2) # INTERNAL_BPM_EXTERNAL_TRANSPORT
        self.sequencer.internal_bpm = 133.0

        # Should respond to transport
        self.sequencer.start()
        self.assertEqual(self.sequencer.state, 'PLAYING')
        self.assertEqual(self.sequencer.get_current_bpm(), 133.0)

        # Should ignore clock
        self.sequencer.handle_clock()
        self.assertEqual(len(self.sequencer._clock_times), 0)
        self.assertEqual(self.sequencer.get_current_bpm(), 133.0)

        self.sequencer.stop()
        self.assertEqual(self.sequencer.state, 'STOPPED')

    def test_internal_mode_ignores_all_midi(self):
        """Test that in pure INTERNAL mode, all transport and clock is ignored."""
        self.sequencer.set_sync_mode(1) # INTERNAL
        self.sequencer.state = 'STOPPED'

        self.sequencer.start()
        self.assertEqual(self.sequencer.state, 'STOPPED')

        self.sequencer.handle_clock()
        self.assertEqual(len(self.sequencer._clock_times), 0)

if __name__ == '__main__':
    unittest.main()

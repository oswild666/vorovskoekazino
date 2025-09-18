from tui import SequencerTUI

def main():
    """
    Main entry point for the application.

    This script launches the Textual user interface, which handles all
    application logic, including MIDI handling and sequencer control.
    """
    app = SequencerTUI()
    app.run()

if __name__ == '__main__':
    main()

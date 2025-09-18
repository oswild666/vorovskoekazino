import time
import sys
from midi_handler import MidiHandler
from sequencer import Sequencer

def main():
    """
    The main application entry point that connects the MIDI handler and sequencer.
    """
    print("--- Polyrhythmic MIDI Sequencer ---")
    print("Initializing...")

    midi_handler = MidiHandler()
    sequencer = Sequencer()

    # --- MIDI Port Selection ---
    available_ports = midi_handler.get_available_ports()

    if not available_ports:
        print("\nError: No MIDI input ports found.")
        print("Please ensure a MIDI device is connected or a virtual MIDI port is active.")
        sys.exit(0)

    print("\nAvailable MIDI input ports:")
    for i, port_name in enumerate(available_ports):
        print(f"  [{i}]: {port_name}")

    selected_index = -1
    while True:
        try:
            choice = input(f"Please select a port (0-{len(available_ports) - 1}): ")
            selected_index = int(choice)
            if 0 <= selected_index < len(available_ports):
                break
            else:
                print(f"Invalid selection. Please enter a number between 0 and {len(available_ports) - 1}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting program.")
            sys.exit(0)

    selected_port = available_ports[selected_index]

    # --- Main Application Loop ---
    try:
        # Wire up the system: connect MIDI callbacks to sequencer actions
        midi_handler.on_start = sequencer.start
        midi_handler.on_stop = sequencer.stop
        midi_handler.on_continue = sequencer.continue_playing
        midi_handler.on_clock = sequencer.handle_clock

        # Attempt to open the selected port
        if not midi_handler.open_port(selected_port):
            print(f"Failed to open port '{selected_port}'. Exiting.")
            sys.exit(1)

        print(f"\nSuccessfully listening to '{selected_port}'.")
        print("Waiting for MIDI clock data. Press Ctrl+C to exit.")

        # The main loop simply keeps the program alive and displays status.
        # All the real work happens in the MidiHandler's background thread.
        while True:
            status_line = sequencer.get_status()
            # Use carriage return '\r' to create a dynamic, single-line status display.
            sys.stdout.write("Status: " + status_line + "   \r")
            sys.stdout.flush()
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nCtrl+C received. Shutting down gracefully...")
    finally:
        # Ensure the MIDI port is always closed on exit.
        midi_handler.close_port()
        print("Application closed.")

if __name__ == '__main__':
    main()

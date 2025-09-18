import mido
import time
import threading

class MidiHandler:
    """
    Handles all MIDI input, including port selection and message listening.
    """
    def __init__(self):
        self.port_name = None
        self.port = None
        self._running = False
        self._listener_thread = None

        # Callbacks for MIDI real-time messages
        self.on_clock = None
        self.on_start = None
        self.on_stop = None
        self.on_continue = None

    @staticmethod
    def get_available_ports():
        """
        Returns a list of available MIDI input port names.
        Handles exceptions if the MIDI system is unavailable.
        """
        try:
            return mido.get_input_names()
        except Exception as e:
            print(f"Warning: Could not retrieve MIDI ports. MIDI system may not be available. Error: {e}")
            return []

    def open_port(self, port_name):
        """
        Opens the specified MIDI input port and starts the listener thread.
        """
        if self._running:
            print("A port is already open. Please close it first.")
            return False

        try:
            self.port = mido.open_input(port_name)
            self.port_name = port_name
            self._running = True
            self._listener_thread = threading.Thread(target=self._listen)
            self._listener_thread.daemon = True
            self._listener_thread.start()
            print(f"Successfully opened MIDI port: {self.port_name}")
            return True
        except Exception as e:
            print(f"Error: Could not open MIDI port '{port_name}'. {e}")
            self.port = None
            return False

    def close_port(self):
        """
        Stops the listener thread and closes the MIDI port.
        """
        if not self._running:
            return

        self._running = False
        if self._listener_thread:
            self._listener_thread.join()
        if self.port:
            self.port.close()
            print(f"Closed MIDI port: {self.port_name}")

        self.port = None
        self.port_name = None

    def _listen(self):
        """
        The internal loop that listens for MIDI messages.
        This runs in a separate thread.
        """
        print("MIDI listener started...")
        while self._running:
            for msg in self.port.iter_pending():
                if msg.type == 'clock' and self.on_clock:
                    self.on_clock()
                elif msg.type == 'start' and self.on_start:
                    self.on_start()
                elif msg.type == 'stop' and self.on_stop:
                    self.on_stop()
                elif msg.type == 'continue' and self.on_continue:
                    self.on_continue()

            time.sleep(0.001)
        print("MIDI listener stopped.")

if __name__ == '__main__':
    print("--- MIDI Handler Test ---")

    ports = MidiHandler.get_available_ports()
    print("Available MIDI input ports:", ports)

    if not ports:
        print("\nNo MIDI input ports found. Exiting test.")
    else:
        selected_port = ports[0]
        print(f"\nAttempting to open port: '{selected_port}'")

        midi_handler = MidiHandler()

        def log_start():
            print("Callback -> START received")

        def log_stop():
            print("Callback -> STOP received")

        def log_continue():
            print("Callback -> CONTINUE received")

        midi_handler.on_start = log_start
        midi_handler.on_stop = log_stop
        midi_handler.on_continue = log_continue

        if midi_handler.open_port(selected_port):
            try:
                print("\nListening for MIDI Start, Stop, Continue messages for 30 seconds.")
                print("Press Ctrl+C to exit early.")
                time.sleep(30)
            except KeyboardInterrupt:
                print("\nKeyboard interrupt received.")
            finally:
                print("Closing port...")
                midi_handler.close_port()
                print("--- Test Finished ---")

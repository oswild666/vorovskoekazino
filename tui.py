import sys
import threading
import time

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, RadioSet, Input, RichLog
from textual.reactive import reactive

from midi_handler import MidiHandler
from sequencer import Sequencer, SYNC_MODES

class SequencerTUI(App):
    """A Textual user interface for the MIDI sequencer."""

    TITLE = "Polyrhythmic MIDI Sequencer"
    CSS_PATH = "tui.css"

    # --- Reactive properties for UI updates ---
    status_dict = reactive(dict)

    def __init__(self):
        super().__init__()
        self.sequencer = Sequencer()
        self.midi_handler = MidiHandler()
        # A lock to ensure thread-safe access to the sequencer
        self.sequencer_lock = threading.Lock()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.log_message("App mounted. Welcome!")
        self.query_one("#log").write("Please select a MIDI port to begin.")
        self.list_midi_ports()

        # Start a background worker to update the UI periodically
        self.update_ui_worker = self.set_interval(1 / 15, self.update_ui, pause=True)

    def compose(self) -> ComposeResult:
        """Create and arrange the widgets for the app."""
        yield Header()
        with Container(id="app-grid"):
            with Vertical(id="left-pane"):
                yield Static("CONTROLS", classes="title")
                yield Static("MIDI Port:", classes="label")
                yield RadioSet(id="midi-port-select")
                yield Static("Sync Mode:", classes="label")
                yield RadioSet(
                    *SYNC_MODES,
                    id="sync-mode-radio"
                )
                yield Static("Internal BPM:", classes="label")
                yield Input(placeholder="120.0", value=str(self.sequencer.internal_bpm), id="bpm-input")
                with Horizontal(classes="buttons"):
                    yield Button("Start", variant="success", id="start-button")
                    yield Button("Stop", variant="error", id="stop-button")

            with Vertical(id="right-pane"):
                yield Static("LIVE STATUS", classes="title")
                yield Static(id="bpm-display")
                yield Static(id="state-display")
                yield Static(id="sync-display")
                yield RichLog(id="log", wrap=True, highlight=True, markup=True)

        yield Footer()

    # --- UI Update Logic ---
    def update_ui(self):
        """Periodically updates the UI with the latest sequencer status."""
        with self.sequencer_lock:
            status = self.sequencer.get_status_dict()

        # Update status displays
        bpm_str = f"BPM: {status['bpm']:.2f}"
        self.query_one("#bpm-display").update(bpm_str)

        state_str = f"State: {status['state']}"
        state_widget = self.query_one("#state-display")
        state_widget.update(state_str)
        # Dynamically apply CSS class for color
        state_widget.remove_class("playing", "stopped")
        state_widget.add_class(status['state'].lower())

        sync_str = f"Sync: {status['sync_mode'].replace('_', ' ')}"
        self.query_one("#sync-display").update(sync_str)

        # Enable/disable controls based on sync mode
        is_internal_transport = status['sync_mode'] == 'INTERNAL'
        self.query_one("#start-button").disabled = not is_internal_transport
        self.query_one("#stop-button").disabled = not is_internal_transport
        self.query_one("#bpm-input").disabled = status['sync_mode'] == 'EXTERNAL'

    def log_message(self, message):
        """Helper to log messages to the RichLog widget."""
        self.query_one("#log").write(f"[{time.strftime('%H:%M:%S')}] {message}")

    # --- MIDI Handling ---
    def list_midi_ports(self):
        """Populates the RadioSet with available MIDI ports."""
        ports = self.midi_handler.get_available_ports()
        port_selector = self.query_one("#midi-port-select")
        if not ports:
            self.log_message("[bold red]No MIDI ports found.[/bold red]")
            port_selector.display = False
            return

        # Create buttons with safe IDs, using the port name as the label
        buttons_to_mount = []
        for i, port_name in enumerate(ports):
            button = Button(port_name, id=f"port_select_{i}")
            buttons_to_mount.append(button)
        port_selector.mount_all(buttons_to_mount)

        self.log_message("Available MIDI ports listed.")

    def start_midi_listener(self, port_name: str) -> None:
        """Starts the MIDI listener in a background thread."""
        self.log_message(f"Attempting to open port: [bold cyan]{port_name}[/bold cyan]")

        # Wire up callbacks
        def midi_callback(func, *args):
            with self.sequencer_lock:
                func(*args)
            self.log_message(f"MIDI Event: {func.__name__}")

        self.midi_handler.on_start = lambda: midi_callback(self.sequencer.start)
        self.midi_handler.on_stop = lambda: midi_callback(self.sequencer.stop)
        self.midi_handler.on_continue = lambda: midi_callback(self.sequencer.continue_playing)
        self.midi_handler.on_clock = lambda: midi_callback(self.sequencer.handle_clock)

        if self.midi_handler.open_port(port_name):
            self.log_message(f"[bold green]Successfully opened {port_name}[/bold green]")
            self.update_ui_worker.resume() # Start updating the UI
        else:
            self.log_message(f"[bold red]Failed to open {port_name}[/bold red]")

    # --- Event Handlers ---
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        # Check if a port selection button was pressed by its ID prefix
        if event.button.id and event.button.id.startswith("port_select_"):
            # The button's label holds the original, unmodified port name
            port_name = str(event.button.label)
            self.run_worker(self.start_midi_listener, port_name)
            self.query_one("#midi-port-select").disabled = True # Disable after selection
        elif event.button.id == "start-button":
            with self.sequencer_lock:
                self.sequencer.state = 'PLAYING'
            self.log_message("Manual Start")
        elif event.button.id == "stop-button":
            with self.sequencer_lock:
                self.sequencer.state = 'STOPPED'
            self.log_message("Manual Stop")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle sync mode changes."""
        if event.radio_set.id == "sync-mode-radio":
            with self.sequencer_lock:
                self.sequencer.set_sync_mode(event.index)
            self.log_message(f"Sync mode changed to [bold yellow]{SYNC_MODES[event.index]}[/bold yellow]")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle BPM input changes."""
        if event.input.id == "bpm-input":
            try:
                bpm = float(event.value)
                if bpm > 0:
                    with self.sequencer_lock:
                        self.sequencer.internal_bpm = bpm
                    self.log_message(f"Internal BPM set to {bpm:.2f}")
            except ValueError:
                pass # Ignore non-float values

    def on_unmount(self) -> None:
        """
        Called when the app is unmounted.
        This is the place for final cleanup.
        """
        self.midi_handler.close_port()
        # Do not try to log here, as widgets may already be gone.

if __name__ == "__main__":
    app = SequencerTUI()
    app.run()

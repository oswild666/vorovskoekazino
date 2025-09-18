import sys
import threading
import time
from functools import partial

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, Checkbox, Input, RichLog
from textual.reactive import reactive
from textual.coordinate import Coordinate

from midi_handler import MidiHandler
from sequencer import Sequencer

class SequencerTUI(App):
    """A Textual user interface for the MIDI sequencer."""

    TITLE = "Polyrhythmic MIDI Sequencer"
    CSS_PATH = "tui.css"

    status_dict = reactive(dict)

    def __init__(self):
        super().__init__()
        self.sequencer = Sequencer()
        self.midi_handler = MidiHandler()
        self.sequencer_lock = threading.Lock()

    def on_mount(self) -> None:
        self.log_message("App mounted. Welcome!")
        self.query_one("#log").write("Please select a MIDI port to begin.")
        self.list_midi_ports()
        self.update_ui_worker = self.set_interval(1 / 15, self.update_ui, pause=True)

    def compose(self) -> ComposeResult:
        """Create and arrange the widgets for the app."""
        yield Header()
        with Horizontal(id="top-bar"):
            yield Button("Play", id="play-button", classes="transport")
            yield Button("Stop", id="stop-button", classes="transport")
            # This button starts hidden and appears after the panel is minimized
            yield Button("Controls", id="restore-controls-button", classes="transport", disabled=True)

        with Container(id="app-grid"):
            with Vertical(id="left-pane"):
                yield Static("CONTROLS", classes="title")
                yield Static("MIDI Port:", classes="label")
                yield Vertical(id="midi-port-select", classes="port-list")
                yield Checkbox("Use Internal BPM", id="internal-bpm-checkbox")
                yield Static("Internal BPM:", classes="label", id="internal-bpm-label")
                yield Input(value=str(self.sequencer.internal_bpm), id="bpm-input")

            with Vertical(id="right-pane"):
                yield Static("LIVE STATUS", classes="title")
                yield Static(id="bpm-display")
                yield Static(id="state-display")
                yield Static(id="sync-display")
                yield RichLog(id="log", wrap=True, highlight=True, markup=True)

        yield Footer()

    def flash_button(self, button: Button, highlight_class: str):
        button.add_class(highlight_class)
        self.set_timer(0.2, lambda: button.remove_class(highlight_class))

    def update_ui(self):
        with self.sequencer_lock:
            status = self.sequencer.get_status_dict()
            trigger_source = status.get("trigger_source")
            if trigger_source != 'INIT':
                self.sequencer.trigger_source = 'INIT'

        if trigger_source and trigger_source != 'INIT':
            highlight_class = f"highlight-{trigger_source.lower()}"
            if status['state'] == 'PLAYING':
                self.flash_button(self.query_one("#play-button"), highlight_class)
            elif status['state'] == 'STOPPED':
                self.flash_button(self.query_one("#stop-button"), highlight_class)

        bpm_str = f"BPM: {status['bpm']:.2f}"
        self.query_one("#bpm-display").update(bpm_str)

        state_str = f"State: {status['state']}"
        state_widget = self.query_one("#state-display")
        state_widget.update(state_str)
        state_widget.remove_class("playing", "stopped")
        state_widget.add_class(status['state'].lower())

        sync_str = f"Sync: {status['sync_mode']}"
        self.query_one("#sync-display").update(sync_str)

        use_internal = self.query_one("#internal-bpm-checkbox").value
        self.query_one("#internal-bpm-label").display = use_internal
        self.query_one("#bpm-input").display = use_internal

    def log_message(self, message):
        self.query_one("#log").write(f"[{time.strftime('%H:%M:%S')}] {message}")

    def list_midi_ports(self):
        ports = self.midi_handler.get_available_ports()
        port_selector = self.query_one("#midi-port-select")
        if not ports:
            self.log_message("[bold red]No MIDI ports found.[/bold red]")
            port_selector.display = False
            return

        buttons_to_mount = [Button(port, id=f"port_select_{i}") for i, port in enumerate(ports)]
        port_selector.mount_all(buttons_to_mount)
        self.log_message("Available MIDI ports listed.")

    def start_midi_listener(self, port_name: str) -> None:
        self.log_message(f"Attempting to open port: [bold cyan]{port_name}[/bold cyan]")

        def midi_callback(func, *args):
            with self.sequencer_lock:
                func(*args, source='MIDI')
            self.log_message(f"MIDI Event: {func.__name__}")

        self.midi_handler.on_start = lambda: midi_callback(self.sequencer.start)
        self.midi_handler.on_stop = lambda: midi_callback(self.sequencer.stop)
        self.midi_handler.on_continue = lambda: midi_callback(self.sequencer.continue_playing)
        self.midi_handler.on_clock = lambda: midi_callback(self.sequencer.handle_clock)

        if self.midi_handler.open_port(port_name):
            self.log_message(f"[bold green]Successfully opened {port_name}[/bold green]")
            self.update_ui_worker.resume()
        else:
            self.log_message(f"[bold red]Failed to open {port_name}[/bold red]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id and button_id.startswith("port_select_"):
            port_name = str(event.button.label)
            work_callable = partial(self.start_midi_listener, port_name)
            self.run_worker(work_callable, thread=True, name=f"MIDI Listener ({port_name})")

            # Animate the controls pane away
            self.query_one("#left-pane").animate("offset", value=Coordinate(0, -50), duration=0.5, easing="in_out_cubic", on_complete=self.show_restore_button)
            self.query_one("#left-pane").animate("opacity", value=0.0, duration=0.4)

        elif button_id == "play-button":
            with self.sequencer_lock:
                self.sequencer.start(source='USER')
            self.log_message("Manual Play")
        elif button_id == "stop-button":
            with self.sequencer_lock:
                self.sequencer.stop(source='USER')
            self.log_message("Manual Stop")
        elif button_id == "restore-controls-button":
            self.query_one("#restore-controls-button").disabled = True
            left_pane = self.query_one("#left-pane")
            left_pane.styles.display = "block"
            left_pane.animate("offset", value=Coordinate(0, 0), duration=0.5, easing="in_out_cubic")
            left_pane.animate("opacity", value=1.0, duration=0.4)

    def show_restore_button(self):
        """Callback to hide the left pane and show the restore button."""
        self.query_one("#left-pane").styles.display = "none"
        self.query_one("#restore-controls-button").disabled = False

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "internal-bpm-checkbox":
            with self.sequencer_lock:
                self.sequencer.use_internal_bpm = event.value
            self.log_message(f"Use Internal BPM set to {event.value}")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "bpm-input":
            try:
                bpm = float(event.value)
                if bpm > 0:
                    with self.sequencer_lock:
                        self.sequencer.internal_bpm = bpm
            except ValueError:
                pass

    def on_unmount(self) -> None:
        self.midi_handler.close_port()

if __name__ == "__main__":
    app = SequencerTUI()
    app.run()

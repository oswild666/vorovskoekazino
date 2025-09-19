import sys
import threading
import time
import random
from functools import partial

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, Checkbox, Input, RichLog, RadioSet, RadioButton
from textual.reactive import reactive
from textual.coordinate import Coordinate
from textual.color import Color

# --- Custom Widget for Background Effect ---

class PatternEditor(Static):
    """A widget to display and edit the sequencer pattern."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grid_buttons = []

    def on_mount(self) -> None:
        self.rebuild_grid()

    def rebuild_grid(self) -> None:
        """Clears and rebuilds the grid of step buttons."""
        # Clear existing buttons
        for button in self.grid_buttons:
            button.remove()
        self.grid_buttons.clear()

        pattern = self.app.sequencer.get_current_pattern()
        if not pattern:
            return

        # Adjust grid size based on pattern
        self.styles.grid_size_rows = len(pattern.tracks)
        self.styles.grid_size_columns = max(t.length for t in pattern.tracks) if pattern.tracks else 16

        # Create new buttons
        for track_index, track in enumerate(pattern.tracks):
            for step_index in range(track.length):
                button = Button("", id=f"step_{track_index}_{step_index}", classes="step-button")
                self.mount(button)
                self.grid_buttons.append(button)

    def update_display(self, current_step: int) -> None:
        """Updates the visual state of the step buttons."""
        pattern = self.app.sequencer.get_current_pattern()
        if not pattern:
            return

        for track_index, track in enumerate(pattern.tracks):
            for step_index in range(track.length):
                button = self.query_one(f"#step_{track_index}_{step_index}")
                button.remove_class("active", "playhead")
                if track.steps[step_index]:
                    button.add_class("active")
                if step_index == current_step % track.length:
                    button.add_class("playhead")

class Starfield(Static):
    """A widget that displays a starfield background with a color cycle."""

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.spawn_star_timer = self.set_interval(1 / 10, self.add_star, pause=True)
        # Start the color animation loop
        self.animate_background_color()

    def add_star(self) -> None:
        """Adds a single star to the starfield."""
        star_char = random.choice(["*", ".", "+", "·"])
        star = Static(star_char)
        star.styles.color = random.choice(["#888", "#aaa", "#ccc", "#fff"])
        star.styles.offset = (
            random.randint(0, self.size.width),
            random.randint(0, self.size.height),
        )
        self.mount(star)

        star.styles.animate(
            "opacity",
            value=0.0,
            duration=random.uniform(2.0, 5.0),
            on_complete=star.remove,
        )

    def animate_background_color(self, to_dark: bool = True):
        """Animates the background color in a loop."""
        target_color = Color.parse("#0d1b2a") if to_dark else Color.parse("#1b263b")
        self.styles.animate(
            "background",
            value=target_color,
            duration=15.0,
            easing="in_out_sine",
            on_complete=lambda: self.animate_background_color(not to_dark)
        )

    def start(self):
        """Starts the star spawning."""
        self.spawn_star_timer.resume()

class SequencerTUI(App):
    """A Textual user interface for the MIDI sequencer."""

    TITLE = "Polyrhythmic MIDI Sequencer"

    CSS = """
    /* --- Top Bar for Transport & Restore Controls --- */
    #top-bar {
        layout: horizontal;
        align: left middle;
        height: 3;
        padding: 0 1;
        background: $panel;
        border-bottom: solid $primary;
    }

    /* --- Windows 3.1 Style Buttons --- */
    Button, .button {
        border: panel $primary-lighten-2;
        background: $panel;
        color: $text;
        min-width: 8;
        height: 1;
        margin: 0 1;
    }

    Button:hover, .button:hover {
        background: $primary-darken-1;
    }

    /* --- Minimize / Restore Buttons --- */
    .restore-button:disabled {
        display: none;
    }

    .minimize-button {
        layer: minimize;
        align: right top;
        width: 3;
        height: 1;
        min-width: 3;
        border: none;
        background: $error;
    }

    /* --- Dynamic Highlighting for Transport Buttons --- */
    Button.highlight-midi {
        background: $secondary;
        color: $text;
    }

    Button.highlight-user {
        background: $success;
        color: $text;
    }

    /* --- Main App Grid --- */
    #app-grid {
        layout: grid;
        grid-size: 3 1;
        grid-gutter: 1;
        padding: 0 1;
        height: 1fr;
        /* Define layers for z-axis positioning */
        layers: base panels;
    }

    /* --- Background Starfield --- */
    Starfield {
        width: 100%;
        height: 100%;
        layer: base; /* Place it on the bottom layer */
    }

    /* --- Main Content Panes --- */
    #left-pane, #right-pane {
        border: heavy $primary;
        padding: 0 1;
        layer: panels; /* Place them on the top layer */
        layers: content minimize;
    }

    #center-pane {
        width: 3fr;
        border: heavy $primary;
        padding: 0 1;
        layer: panels;
    }

    #right-pane {
        width: 2fr;
    }

    PatternEditor {
        layout: grid;
        grid-size: 4 16; /* 4 tracks, 16 steps */
        grid-gutter: 1;
        width: 100%;
        height: 100%;
    }

    /* --- Common Styles --- */
    .title {
        background: $primary;
        color: $text;
        width: 100%;
        padding: 0;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    .label {
        text-style: bold;
        margin-top: 1;
    }

    /* --- Specific Widget Styling --- */
    .port-list Button {
        width: 100%;
        margin-bottom: 1;
    }

    Checkbox {
        margin-top: 1;
    }

    Input {
        margin-top: 1;
    }

    /* Status display styling */
    #bpm-display, #state-display, #sync-display {
        border: tall $background-lighten-2;
        background: $background-darken-2;
        padding: 0 1;
        margin-bottom: 1;
        height: 1;
        text-style: bold;
    }

    #state-display.stopped {
        color: $error;
    }

    #state-display.playing {
        color: $success;
    }

    #log {
        border: panel $primary-lighten-2;
        height: 1fr;
    }

    .step-button {
        width: 100%;
        height: 100%;
        background: $panel-lighten-2;
        border: none;
    }

    .step-button.active {
        background: $success;
    }

    .step-button.playhead {
        border: thick $secondary;
    }
    """

    status_dict = reactive(dict)

    def __init__(self):
        super().__init__()
        # Import locally to avoid potential import cycle/path issues
        from sequencer import Sequencer
        from midi_handler import MidiHandler

        self.sequencer = Sequencer()
        self.midi_handler = MidiHandler()
        self.sequencer_lock = threading.Lock()

    def on_mount(self) -> None:
        self.log_message("App mounted. Welcome!")
        self.query_one("#log").write("Please select a MIDI port to begin.")
        self.list_midi_ports()
        self.update_ui_worker = self.set_interval(1 / 15, self.update_ui, pause=True)
        self.query_one(Starfield).start()

    def compose(self) -> ComposeResult:
        """Create and arrange the widgets for the app."""
        yield Header()
        with Horizontal(id="top-bar"):
            yield Button("Play", id="play-button", classes="transport")
            yield Button("Stop", id="stop-button", classes="transport")
            yield Button("Controls", id="restore-controls", classes="restore-button", disabled=True)
            yield Button("Status", id="restore-status", classes="restore-button", disabled=True)

        with Container(id="app-grid"):
            yield Starfield()
            with Vertical(id="left-pane"):
                yield Static("CONTROLS", classes="title")
                yield Button("﹣", id="minimize-controls", classes="minimize-button")
                yield Static("MIDI Port:", classes="label")
                yield Vertical(id="midi-port-select", classes="port-list")
                yield Checkbox("Sync to MIDI Start/Stop", id="sync-transport-checkbox", value=True)
                yield Static("BPM Source:", classes="label")
                with RadioSet(id="bpm-source-radioset"):
                    yield RadioButton("External MIDI Clock", id="bpm-external", value=True)
                    yield RadioButton("Internal", id="bpm-internal")
                yield Static("Internal BPM:", classes="label", id="internal-bpm-label")
                yield Input(value=str(self.sequencer.internal_bpm), id="bpm-input")

                yield Static("\n--- Patterns ---", classes="label")
                yield Static("Pattern switching coming soon...", id="pattern-switcher-placeholder")

            with Vertical(id="center-pane"):
                yield PatternEditor()

            with Vertical(id="right-pane"):
                yield Static("LIVE STATUS", classes="title")
                yield Button("﹣", id="minimize-status", classes="minimize-button")
                yield Static(id="bpm-display")
                yield Static(id="state-display")
                yield Static(id="sync-display")
                yield RichLog(id="log", wrap=True, highlight=True, markup=True)

        yield Footer()

    def minimize_panel(self, panel_selector: str, restore_button_selector: str):
        panel = self.query_one(panel_selector)
        def show_restore_button():
            panel.styles.display = "none"
            self.query_one(restore_button_selector).disabled = False
        panel.styles.animate("offset", value=(0, -panel.outer_size.height), duration=0.5, easing="in_out_cubic", on_complete=show_restore_button)
        panel.styles.animate("opacity", value=0.0, duration=0.4)

    def restore_panel(self, panel_selector: str, restore_button_selector: str):
        self.query_one(restore_button_selector).disabled = True
        panel = self.query_one(panel_selector)
        panel.styles.display = "block"
        panel.styles.animate("offset", value=(0, 0), duration=0.5, easing="in_out_cubic")
        panel.styles.animate("opacity", value=1.0, duration=0.4)

    def flash_button(self, button: Button, highlight_class: str):
        button.add_class(highlight_class)
        self.set_timer(0.2, lambda: button.remove_class(highlight_class))

    def update_ui(self):
        current_time = time.monotonic()
        with self.sequencer_lock:
            self.sequencer.tick(current_time)
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

        sync_str = f"BPM Source: {status['bpm_source']}"
        self.query_one("#sync-display").update(sync_str)

        is_internal_bpm = status['bpm_source'] == 'INTERNAL'
        self.query_one("#internal-bpm-label").display = is_internal_bpm
        self.query_one("#bpm-input").display = is_internal_bpm

        self.query_one(PatternEditor).update_display(status['current_step'])

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
            self.minimize_panel("#left-pane", "#restore-controls")
        else:
            self.log_message(f"[bold red]Failed to open {port_name}[/bold red]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id and button_id.startswith("port_select_"):
            port_name = str(event.button.label)
            work_callable = partial(self.start_midi_listener, port_name)
            self.run_worker(work_callable, thread=True, name=f"MIDI Listener ({port_name})")

        elif button_id == "play-button":
            with self.sequencer_lock:
                self.sequencer.start(source='USER')
            self.log_message("Manual Play")
        elif button_id == "stop-button":
            with self.sequencer_lock:
                self.sequencer.stop(source='USER')
            self.log_message("Manual Stop")

        elif button_id == "minimize-controls":
            self.minimize_panel("#left-pane", "#restore-controls")
        elif button_id == "minimize-status":
            self.minimize_panel("#right-pane", "#restore-status")
        elif button_id == "restore-controls":
            self.restore_panel("#left-pane", "#restore-controls")
        elif button_id and button_id.startswith("step_"):
            parts = button_id.split("_")
            track_index = int(parts[1])
            step_index = int(parts[2])
            with self.sequencer_lock:
                pattern = self.sequencer.get_current_pattern()
                if pattern and track_index < len(pattern.tracks):
                    pattern.tracks[track_index].toggle_step(step_index)

        elif button_id == "restore-status":
            self.restore_panel("#right-pane", "#restore-status")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "sync-transport-checkbox":
            with self.sequencer_lock:
                self.sequencer.sync_transport = event.value
            self.log_message(f"Sync to MIDI Start/Stop set to {event.value}")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "bpm-source-radioset":
            new_source = "INTERNAL" if event.pressed.id == "bpm-internal" else "EXTERNAL"
            with self.sequencer_lock:
                self.sequencer.bpm_source = new_source
            self.log_message(f"BPM Source set to {new_source}")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "bpm-input":
            try:
                bpm = float(event.value)
                if bpm > 0:
                    with self.sequencer_lock:
                        self.sequencer.internal_bpm = bpm
                    self.log_message(f"Internal BPM set to {bpm}")
            except ValueError:
                pass

    def on_unmount(self) -> None:
        self.midi_handler.close_port()

if __name__ == "__main__":
    app = SequencerTUI()
    app.run()

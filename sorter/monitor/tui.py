from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, RichLog
from textual.reactive import reactive
import time
from rich.text import Text

from sorter.util.time_delta_format import time_delta_format


class MonitorApp(App):
    """A Textual app to monitor the brick sorter services."""

    CSS_PATH = "tui.css"
    BINDINGS = [
        ("r", "restart_all", "Restart All"),
        ("q", "quit", "Quit"),
    ]

    services = reactive([])
    messages = reactive([])

    def __init__(self, monitor, **kwargs):
        super().__init__(**kwargs)
        self.monitor = monitor

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(name="Brick Sorter Monitor")
        yield DataTable(id="services")
        yield RichLog(id="messages", wrap=True, highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        table = self.query_one(DataTable)
        table.add_columns("Service", "PID", "Status", "Uptime", "Restarts")
        self.update_timer = self.set_interval(1, self.update_data)

    def update_data(self) -> None:
        """Update the data for the TUI."""
        self.services = self.monitor.get_services()
        self.messages = self.monitor.get_messages()

        # Update the table
        table = self.query_one(DataTable)
        table.clear()
        for service in self.services:
            uptime_str = "N/A"
            if service.final_uptime_seconds is not None:
                uptime_str = time_delta_format(service.final_uptime_seconds)
            elif service.start_time:
                uptime_seconds = int(time.time() - service.start_time)
                uptime_str = time_delta_format(uptime_seconds)

            restarts = f"{service.remaining_restarts}/{service.restart_attempts}"
            if service.restart_attempts == -1:
                restarts = f"{service.remaining_restarts}/inf"

            style = self.get_status_style(service.display_status)
            table.add_row(
                Text(service.name, style=style),
                str(service.pid or "N/A"),
                service.display_status,
                uptime_str,
                restarts,
                key=service.name,
            )

        # Update messages
        log = self.query_one(RichLog)
        log.clear()
        for msg in self.messages:
            log.write(msg)

    def get_status_style(self, status: str) -> str:
        """Return the CSS style for a given status."""
        return {
            "RUNNING": "green",
            "ERROR": "red",
            "STOPPED": "gray",
            "WARN": "yellow",
            "WAITING": "blue",
            "STARTING": "blue",
            "RESTARTING": "blue",
        }.get(status, "white")

    def action_restart_all(self) -> None:
        """An action to restart all services."""
        self.monitor.restart_all_services()

    def action_quit(self) -> None:
        """An action to quit the app."""
        self.monitor.shutdown()
        self.exit()

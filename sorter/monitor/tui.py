import curses
import logging
import time
from typing import List

from sorter.monitor.service import Service
from sorter.util.time_delta_format import time_delta_format


class TUI:
    """Manages rendering the terminal user interface using curses."""

    def __init__(self):
        self.stdscr = None
        self._init_colors()

    def _init_colors(self):
        self.colors = {}
        # Define color pairs. The TUI manager will initialize them.
        self.COLOR_GREEN = 1
        self.COLOR_RED = 2
        self.COLOR_YELLOW = 3
        self.COLOR_BLUE = 4
        self.COLOR_GRAY = 5
        self.COLOR_WHITE = 6

    def _setup_curses(self, stdscr):
        """Initializes the curses screen and color pairs."""
        self.stdscr = stdscr
        curses.curs_set(0)  # Hide cursor
        self.stdscr.nodelay(1)  # Non-blocking input

        if curses.has_colors():
            curses.start_color()
            curses.init_pair(self.COLOR_GREEN, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_RED, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_YELLOW, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_BLUE, curses.COLOR_BLUE, curses.COLOR_BLACK)
            curses.init_pair(
                self.COLOR_GRAY, curses.COLOR_WHITE, curses.COLOR_BLACK
            )  # Bright gray
            curses.init_pair(self.COLOR_WHITE, curses.COLOR_WHITE, curses.COLOR_BLACK)

    def _get_status_color(self, status: str) -> int:
        """Returns the color pair for a given service status."""
        status_map = {
            "RUNNING": self.COLOR_GREEN,
            "ERROR": self.COLOR_RED,
            "STOPPED": self.COLOR_GRAY,
            "WARN": self.COLOR_YELLOW,
            "WAITING": self.COLOR_BLUE,
            "STARTING": self.COLOR_BLUE,
            "RESTARTING": self.COLOR_BLUE,
        }
        return curses.color_pair(status_map.get(status, self.COLOR_WHITE))

    def _draw_table(self, services: List[Service]):
        """Draws the main table of services."""
        h, w = self.stdscr.getmaxyx()
        header = "Service                | PID    | Status   | Uptime   | Restarts"
        self.stdscr.addstr(1, 1, "+" + "-" * (w - 3) + "+")
        self.stdscr.addstr(2, 2, header)
        self.stdscr.addstr(3, 1, "+" + "-" * (w - 3) + "+")

        for i, service in enumerate(services):
            y = 4 + i
            if y >= h - 5:
                break  # Stop drawing if we run out of space

            status = service.display_status
            color = self._get_status_color(status)

            name = service.name[:22].ljust(22)
            pid = str(service.pid or "N/A").ljust(6)
            status_str = status.ljust(8)

            uptime_str = "N/A"
            if service.final_uptime_seconds is not None:
                uptime_str = time_delta_format(service.final_uptime_seconds)
            elif service.start_time:
                uptime_seconds = int(time.time() - service.start_time)
                uptime_str = time_delta_format(uptime_seconds)
            uptime_str = uptime_str.ljust(8)

            restarts = f"{service.remaining_restarts}/{service.restart_attempts}"
            if service.restart_attempts == -1:
                restarts = f"{service.remaining_restarts}/inf"
            restarts = restarts.ljust(8)

            line = f"{name} | {pid} | {status_str} | {uptime_str} | {restarts}"
            self.stdscr.addstr(y, 2, line, color)

        self.stdscr.addstr(4 + len(services), 1, "+" + "-" * (w - 3) + "+")

    def _draw_messages(self, messages: List[str], services_count: int):
        """Draws the recent messages panel."""
        h, w = self.stdscr.getmaxyx()

        # Position the message panel after the service table.
        # Table uses 4 rows for header/borders + 1 row per service.
        panel_y_start = 4 + services_count + 2

        # If there's not enough space for the panel header and at least one message, don't draw.
        if panel_y_start > h - 4:
            return

        title = "Recent Messages (Last 8)"
        self.stdscr.addstr(panel_y_start - 1, 1, "+" + "-" * (w - 3) + "+")
        self.stdscr.addstr(panel_y_start, 2, title)

        for i, msg in enumerate(messages):
            y = panel_y_start + 1 + i
            # Stop if we are about to hit the footer or have drawn 8 messages.
            if i >= 8 or y >= h - 2:
                break

            color_pair = self.COLOR_WHITE
            if "ERROR" in msg:
                color_pair = self.COLOR_RED
            elif "WARN" in msg:
                color_pair = self.COLOR_YELLOW

            self.stdscr.addstr(y, 2, msg[: w - 4], curses.color_pair(color_pair))

        # Calculate where the bottom border should be.
        num_messages_drawn = min(len(messages), 8)
        bottom_y = min(panel_y_start + 1 + num_messages_drawn, h - 2)
        self.stdscr.addstr(bottom_y, 1, "+" + "-" * (w - 3) + "+")

    def draw(self, monitor):
        """Main drawing function, called in the loop."""
        h, w = self.stdscr.getmaxyx()
        self.stdscr.clear()

        # Header
        log_path_str = f"Brick Sorter Monitor - {monitor.process_manager.log_dir}"
        self.stdscr.addstr(0, 1, log_path_str[: w - 2])

        # Table
        services = monitor.get_services()
        self._draw_table(services)

        # Messages
        self._draw_messages(monitor.get_messages(), len(services))

        # Footer
        footer = "Q: Quit | R: Restart All"
        self.stdscr.addstr(h - 1, 1, footer)

        self.stdscr.refresh()

    def run(self, stdscr, monitor):
        """The main loop for the TUI, wrapped by curses.wrapper."""
        self._setup_curses(stdscr)

        while not monitor.is_shutting_down():
            self.draw(monitor)

            # Handle user input
            key = self.stdscr.getch()
            if key == ord("q") or key == ord("Q"):
                monitor.shutdown()
            elif key == ord("r") or key == ord("R"):
                logging.info("User requested restart of all services.")
                monitor.restart_all_services()

            time.sleep(0.2)  # Refresh rate

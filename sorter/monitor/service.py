import dataclasses
import pathlib
import subprocess
from typing import Dict, List, Optional


@dataclasses.dataclass
class Service:
    """Represents a single service managed by the supervisor."""

    # Properties from the configuration file
    name: str
    command: str
    enabled: bool
    args: Dict[str, str]
    restart_attempts: int
    depends_on: List[str]
    startup_delay_seconds: int

    # Runtime state properties
    status: str = "STOPPED"
    pid: Optional[int] = None
    start_time: Optional[float] = None
    process: Optional[subprocess.Popen] = None
    log_file: Optional[pathlib.Path] = None
    remaining_restarts: int = 0
    # The 'WARN' status is a special case. The process is still running,
    # but we want to highlight it in the TUI.
    has_warned: bool = False
    # To store the final uptime when a process stops
    final_uptime_seconds: Optional[int] = None

    def __post_init__(self):
        """Initializes remaining_restarts after the object is created."""
        self.remaining_restarts = self.restart_attempts

    @property
    def display_status(self) -> str:
        """Returns the status to be displayed in the TUI, accounting for warnings."""
        if self.status == "RUNNING" and self.has_warned:
            return "WARN"
        return self.status

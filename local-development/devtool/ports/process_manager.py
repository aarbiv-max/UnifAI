"""Port: process manager for launching/killing processes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ProcessManager(ABC):

    @abstractmethod
    def kill_port(self, port: int) -> None:
        """Kill any process listening on the given port."""

    @abstractmethod
    def is_port_in_use(self, port: int) -> bool:
        """Return True if something is listening on the port."""

    @abstractmethod
    def run_command(
        self,
        cmd: list[str],
        cwd: Path,
        *,
        log_file: Path | None = None,
    ) -> None:
        """Run a command synchronously.

        If *log_file* is provided, stdout is appended there and only stderr
        is shown on the terminal.  Raises on non-zero exit.
        """

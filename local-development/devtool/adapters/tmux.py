"""Adapter: tmux session manager."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from devtool.domain.models import Service, WindowLayout
from devtool.ports.session_manager import SessionManager


class TmuxSessionManager(SessionManager):
    """Manages services inside a tmux session with auto-windowing."""

    def launch(
        self,
        session_name: str,
        layout: list[WindowLayout],
        commands: dict[str, str],
        log_dir: Path,
    ) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        self.kill_session(session_name)

        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name],
            check=True,
        )

        for i, window in enumerate(layout):
            if i == 0:
                subprocess.run(
                    ["tmux", "rename-window", "-t", f"{session_name}:0", window.name],
                    check=True,
                )
            else:
                subprocess.run(
                    ["tmux", "new-window", "-t", session_name, "-n", window.name],
                    check=True,
                )
            self._populate_window(
                session_name, window.name, window.services, commands, log_dir,
            )

        subprocess.run(
            ["tmux", "select-window", "-t", f"{session_name}:0"],
            check=False,
        )

    def attach(self, session_name: str) -> None:
        subprocess.run(
            ["tmux", "attach-session", "-t", session_name],
            check=False,
        )

    def kill_session(self, session_name: str) -> None:
        subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True,
        )

    def is_running(self, session_name: str) -> bool:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
        )
        return result.returncode == 0

    def graceful_stop(self, session_name: str, timeout: int = 10) -> None:
        if not self.is_running(session_name):
            return

        pane_ids = self._list_pane_ids(session_name)
        for pane_id in pane_ids:
            subprocess.run(
                ["tmux", "send-keys", "-t", pane_id, "C-c", ""],
                capture_output=True,
            )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.is_running(session_name):
                return
            time.sleep(1)

        self.kill_session(session_name)

    def _list_pane_ids(self, session_name: str) -> list[str]:
        result = subprocess.run(
            [
                "tmux", "list-panes", "-s", "-t", session_name,
                "-F", "#{pane_id}",
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]

    def pane_contents(self, session_name: str) -> dict[str, str]:
        if not self.is_running(session_name):
            return {}

        result = subprocess.run(
            [
                "tmux", "list-panes", "-s", "-t", session_name,
                "-F", "#{window_index}.#{pane_index}\t#{pane_id}",
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return {}

        panes: dict[str, str] = {}
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            pane_ref, pane_id = parts
            capture = subprocess.run(
                ["tmux", "capture-pane", "-t", pane_id, "-p", "-S", "-50"],
                capture_output=True, text=True,
            )
            panes[pane_ref] = capture.stdout
        return panes

    def _populate_window(
        self,
        session_name: str,
        window_name: str,
        services: list[Service],
        commands: dict[str, str],
        log_dir: Path,
    ) -> None:
        """Create one pane per service inside *window_name* with tiled layout."""
        target = f"{session_name}:{window_name}"
        for i, svc in enumerate(services):
            if i > 0:
                subprocess.run(
                    ["tmux", "split-window", "-t", target],
                    check=True,
                )
                subprocess.run(
                    ["tmux", "select-layout", "-t", target, "tiled"],
                    check=True,
                )

            cmd = commands[svc.name]
            log_path = log_dir / f"{svc.name}.log"
            wrapped = f"{cmd} 2>&1 | tee {log_path}"
            pane_target = f"{target}.{i}"
            subprocess.run(
                ["tmux", "send-keys", "-t", pane_target, wrapped, "C-m"],
                check=True,
            )

        subprocess.run(
            ["tmux", "select-layout", "-t", target, "tiled"],
            check=False,
        )

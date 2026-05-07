"""Adapter: foreground session manager for single-service mode."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from devtool.domain.models import Service, ServiceType
from devtool.ports.session_manager import SessionManager


def _resolve_bash() -> str:
    """Find bash on PATH instead of assuming /bin/bash."""
    path = shutil.which("bash")
    if not path:
        raise RuntimeError(
            "bash not found on PATH. Install bash or set SHELL to a compatible shell."
        )
    return path


class ForegroundSessionManager(SessionManager):
    """Runs a single primary service in the current terminal via exec."""

    def launch(
        self,
        session_name: str,
        layout: list[WindowLayout],
        commands: dict[str, str],
        log_dir: Path,
    ) -> None:
        all_services = [s for w in layout for s in w.services]
        if len(all_services) != 1:
            raise RuntimeError(
                "Foreground mode requires exactly one service, "
                f"got {len(all_services)}."
            )
        svc = all_services[0]
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{svc.name}.log"

        print(f"\n🚀 Starting {svc.name} …")
        print("   Press Ctrl+C to stop.\n")

        cmd = commands[svc.name]
        shell_cmd = f"{cmd} 2>&1 | tee {log_path}"
        bash = _resolve_bash()
        os.execvp(bash, [bash, "-c", shell_cmd])

    def attach(self, session_name: str) -> None:
        pass

    def kill_session(self, session_name: str) -> None:
        pass

    def is_running(self, session_name: str) -> bool:
        return False

    def graceful_stop(self, session_name: str, timeout: int = 10) -> None:
        pass

    def pane_contents(self, session_name: str) -> dict[str, str]:
        return {}

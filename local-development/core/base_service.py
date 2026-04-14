"""Abstract base class defining the contract every local-development service must implement."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.local_dev_config import LocalDevConfig


@dataclass
class PatchSpec:
    """Declarative description of a text replacement in a source file."""

    file: Path
    find: str
    replace: str


class BaseService(ABC):
    """
    Each concrete service encapsulates its own venv setup, .env generation,
    source-file patches, and run command so the orchestrator can treat all
    services uniformly.
    """

    def __init__(self, root: Path, config: LocalDevConfig) -> None:
        self._root = root
        self._config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier used on the CLI (e.g. 'rag', 'multi-agent')."""

    @property
    @abstractmethod
    def directory(self) -> Path:
        """Relative path from repo root to the service directory."""

    @property
    def absolute_directory(self) -> Path:
        return self._root / self.directory

    @property
    def port(self) -> int | None:
        return None

    @property
    def required_infrastructure(self) -> list[str]:
        """Container names this service depends on (e.g. ['mongo', 'rabbitmq'])."""
        return []

    @property
    def is_primary(self) -> bool:
        """True for the canonical owner of its venv directory.

        Workers that share a venv with another service should return False
        so that ``setup_venvs`` deduplicates correctly.
        """
        return True

    def venv_build_commands(self, python: str) -> list[list[str]]:
        """Ordered shell commands to create and populate the virtual environment.

        The default covers Python services with a requirements.txt and
        global_utils dependency.
        """
        reqs = self.absolute_directory / "requirements.txt"
        if not reqs.exists():
            return []
        global_utils_rel = os.path.relpath(
            self._root / "global_utils", self.absolute_directory,
        )
        return [
            [python, "-m", "venv", "venv"],
            ["venv/bin/pip", "install", "-r", "requirements.txt"],
            ["venv/bin/pip", "install", "-e", global_utils_rel],
        ]

    @property
    def venv_success_message(self) -> str:
        """Message printed after a successful venv setup."""
        return f"All requirements and packages for {self.name} installed successfully."

    def env_entries(self) -> dict[str, str] | None:
        """Key-value pairs to write into a .env file, or None if not needed."""
        return None

    @property
    def env_file_path(self) -> Path | None:
        """Absolute path to the .env file this service needs, or None."""
        return None

    def patch_specs(self) -> list[PatchSpec]:
        """Declarative patches for local development.
            Each PatchSpec describes a find/replace in a file (path relative to
            repo root).
        """
        return []

    def post_apply_message(self) -> str | None:
        """Optional message shown after .env generation / patching."""
        return None

    @abstractmethod
    def run_command(self) -> str:
        """Full shell command string to start this service (foreground / tmux)."""

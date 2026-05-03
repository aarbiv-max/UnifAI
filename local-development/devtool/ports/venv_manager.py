"""Port: virtual-environment manager."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from devtool.domain.models import Service


class VenvManager(ABC):

    @abstractmethod
    def create(
        self, service: Service, python: str, root: Path,
        *, log_dir: Path | None = None, force: bool = False,
    ) -> None:
        """Create and populate a virtual environment for the service.

        When *log_dir* is given, verbose install output is redirected to
        ``{log_dir}/{service.name}.log`` instead of printing to stdout.

        When *force* is True, an existing venv is deleted and recreated.
        When False, an existing venv is left as-is (the call is a no-op).
        """

    @abstractmethod
    def verify(self, service: Service, python_minor: str, root: Path) -> None:
        """Verify the venv exists and its Python matches *python_minor*.

        Raises RuntimeError on mismatch or missing venv.
        """

    @abstractmethod
    def exists(self, service: Service, root: Path) -> bool:
        """Return True if the venv directory already exists."""

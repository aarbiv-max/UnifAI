"""Port: Python interpreter resolution."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PythonResolver(ABC):

    @abstractmethod
    def find_python(
        self,
        python_min: tuple[int, int],
        python_max: tuple[int, int],
        *,
        env_override: str | None = None,
    ) -> str:
        """Find a suitable Python interpreter within the given version range.

        *env_override* is an explicit interpreter path/name (e.g. from
        ``UNIFAI_PYTHON``).  When provided, only that candidate is tried.

        Returns the resolved path.  Raises RuntimeError when no valid
        interpreter is found.
        """

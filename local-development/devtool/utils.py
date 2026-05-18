"""Shared utilities — layer-neutral helpers usable by both adapters and services."""

from __future__ import annotations

import shutil


def resolve_bash() -> str:
    """Find bash on PATH instead of assuming /bin/bash."""
    path = shutil.which("bash")
    if not path:
        raise RuntimeError(
            "bash not found on PATH. Install bash or set SHELL to a compatible shell."
        )
    return path

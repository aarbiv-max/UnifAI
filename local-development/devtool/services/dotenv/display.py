"""Display .env file contents to stdout."""

from __future__ import annotations

from pathlib import Path

from devtool.domain.models import Service


def show(service: Service, root: Path) -> None:
    """Print the current .env config for *service*."""
    if not service.env_file:
        print(f"{service.name}: no env file configured.")
        return

    env_path = root / service.directory / service.env_file
    if env_path.exists():
        print(f"── {env_path} ──")
        print(env_path.read_text(), end="")
    else:
        print(f"{env_path} does not exist yet.")
        if service.env_entries:
            print("Template values:")
            for k, v in service.env_entries.items():
                print(f"  {k}={v}")

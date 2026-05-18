"""Identity-service local_auth alignment."""

from __future__ import annotations

from pathlib import Path

from devtool.domain.models import Service

from .common import LOCAL_AUTH_SERVICE


def align_local_auth(service: Service, root: Path, *, local_auth: bool) -> bool:
    """Ensure identity's ``local_auth_enabled`` line matches the flag.

    When *local_auth* is true, appends ``local_auth_enabled=true`` if absent.
    When false, removes any ``local_auth_enabled`` line.

    Returns True if the file was modified.
    """
    if service.name != LOCAL_AUTH_SERVICE or not service.env_file:
        return False

    env_path = root / service.directory / service.env_file
    if not env_path.exists():
        return False

    lines = env_path.read_text().splitlines(keepends=True)
    has_key = any(
        line.lstrip().startswith("local_auth_enabled=")
        for line in lines
        if not line.lstrip().startswith("#")
    )

    if local_auth and not has_key:
        with open(env_path, "a") as f:
            f.write("local_auth_enabled=true\n")
        return True

    if not local_auth and has_key:
        with open(env_path, "w") as f:
            for line in lines:
                if not line.lstrip().startswith("local_auth_enabled="):
                    f.write(line)
        return True

    return False

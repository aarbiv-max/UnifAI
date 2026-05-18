"""Mutation of existing .env files and shared secret management."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from devtool.domain.models import Service

from .common import SECRET_KEY_FILE


def get_or_create_shared_secret(root: Path) -> str:
    """Return the shared dev secret, creating it on first call.

    The key is persisted to ``local-development/.dev-secret-key``
    and is the same across all services.
    """
    secret_path = root / SECRET_KEY_FILE
    if secret_path.exists():
        value = secret_path.read_text().strip()
        if value:
            return value
    key = secrets.token_hex(32)
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(secret_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key + "\n")
    return key


def replace_env_value(env_path: Path, key: str, new_value: str) -> None:
    """Rewrite a single ``key=...`` line in an env file."""
    lines = env_path.read_text().splitlines(keepends=True)
    with open(env_path, "w") as f:
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith(f"{key}="):
                f.write(f"{key}={new_value}\n")
            else:
                f.write(line)


def resolve_auto_generate_key(
    key: str, value: str, services: list[Service], root: Path,
) -> int:
    """Write *value* for *key* into every service's on-disk .env file.

    Returns the number of files updated.
    """
    updated = 0
    for svc in services:
        if not svc.env_file:
            continue
        env_path = root / svc.directory / svc.env_file
        if not env_path.exists():
            continue
        replace_env_value(env_path, key, value)
        updated += 1
    return updated

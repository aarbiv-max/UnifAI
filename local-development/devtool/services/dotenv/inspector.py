"""Read-only analysis of .env files: unresolved markers and missing keys."""

from __future__ import annotations

from pathlib import Path

from devtool.domain.models import Service
from devtool.domain.registry import Registry

from .common import AUTOGEN_RE, PLACEHOLDER_RE, expected_keys


def check_missing_keys(
    service: Service, root: Path, *, local_auth: bool = False,
) -> set[str]:
    """Return env-entry keys expected but absent from the on-disk file."""
    if not service.env_file or not service.env_entries:
        return set()

    env_path = root / service.directory / service.env_file
    if not env_path.exists():
        return set()

    exp = expected_keys(service, local_auth=local_auth)

    on_disk: set[str] = set()
    with open(env_path) as f:
        for line in f:
            stripped = line.lstrip()
            if not stripped or stripped[0] == "#":
                continue
            eq = stripped.find("=")
            if eq == -1:
                continue
            on_disk.add(stripped[:eq].rstrip())

    return exp - on_disk


def check_unresolved(
    service: Service, root: Path,
) -> tuple[set[str], set[str]]:
    """Return ``(placeholders, auto_generate)`` — keys still unresolved on disk."""
    empty: tuple[set[str], set[str]] = (set(), set())
    if not service.env_file or not service.env_entries:
        return empty

    placeholder_suspects = {
        key for key, value in service.env_entries.items()
        if PLACEHOLDER_RE.search(value)
    }
    autogen_suspects = {
        key for key, value in service.env_entries.items()
        if AUTOGEN_RE.search(value)
    }
    all_suspects = placeholder_suspects | autogen_suspects
    if not all_suspects:
        return empty

    env_path = root / service.directory / service.env_file
    if not env_path.exists():
        return empty

    placeholders: set[str] = set()
    auto_gen: set[str] = set()

    with open(env_path) as f:
        for line in f:
            if not all_suspects:
                break
            stripped = line.lstrip()
            if not stripped or stripped[0] == "#":
                continue
            eq = stripped.find("=")
            if eq == -1:
                continue
            key = stripped[:eq].rstrip()
            if key not in all_suspects:
                continue
            value_start = stripped[eq + 1:eq + 20]
            if key in placeholder_suspects and PLACEHOLDER_RE.search(value_start):
                placeholders.add(key)
            if key in autogen_suspects and AUTOGEN_RE.search(value_start):
                auto_gen.add(key)
            all_suspects.discard(key)

    return placeholders, auto_gen


def check_placeholders(service: Service, root: Path) -> set[str]:
    """Return env-entry keys whose ``<REPLACE...>`` marker is still on disk."""
    placeholders, _ = check_unresolved(service, root)
    return placeholders


def check_auto_generate(service: Service, root: Path) -> set[str]:
    """Return env-entry keys whose ``<AUTO_GENERATE>`` marker is still on disk."""
    _, auto_gen = check_unresolved(service, root)
    return auto_gen


def collect_auto_generate_keys(registry: Registry, root: Path) -> dict[str, list[str]]:
    """Return ``{key: [service_names...]}`` for all unresolved auto-generate entries."""
    grouped: dict[str, list[str]] = {}
    for svc in registry.all_services():
        _, auto_gen = check_unresolved(svc, root)
        for key in auto_gen:
            grouped.setdefault(key, []).append(svc.name)
    return grouped

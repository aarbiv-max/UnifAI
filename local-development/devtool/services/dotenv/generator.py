"""File creation and update logic for .env files."""

from __future__ import annotations

from pathlib import Path

from devtool.domain.registry import Registry

from .common import ENV_HEADER, KEYCLOAK_KEYS, LOCAL_AUTH_SERVICE, GenerateResult
from .inspector import check_missing_keys, check_unresolved
from .local_auth import align_local_auth


def generate(
    service, root: Path, *, force: bool = False, local_auth: bool = False,
) -> GenerateResult:
    """Write or update the .env file for *service*.

    When *local_auth* is true and the service is ``identity``, Keycloak
    placeholder keys are omitted and ``local_auth_enabled=true`` is written
    instead.

    Returns ``CREATED`` for a new file, ``UPDATED`` if missing keys were
    appended to an existing file, or ``SKIPPED`` if nothing changed.
    """
    if not service.env_entries or not service.env_file:
        return GenerateResult.SKIPPED

    env_path = root / service.directory / service.env_file

    if env_path.exists() and not force:
        missing = check_missing_keys(service, root, local_auth=local_auth)
        if not missing:
            return GenerateResult.SKIPPED
        new_lines: list[str] = []
        for key in missing:
            if key == "local_auth_enabled":
                new_lines.append("local_auth_enabled=true\n")
            else:
                new_lines.append(f"{key}={service.env_entries[key]}\n")
        with open(env_path, "a") as f:
            f.writelines(new_lines)
        return GenerateResult.UPDATED

    is_identity_local = local_auth and service.name == LOCAL_AUTH_SERVICE

    lines = [ENV_HEADER]
    for key, value in service.env_entries.items():
        if is_identity_local and key in KEYCLOAK_KEYS:
            continue
        lines.append(f"{key}={value}\n")

    if is_identity_local:
        lines.append("local_auth_enabled=true\n")

    env_path.write_text("".join(lines))
    return GenerateResult.CREATED


def generate_all(
    registry: Registry, root: Path, *, force: bool = False,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Generate .env files for every service that needs one.

    Returns ``(generated, skipped, updated, warnings)``.
    """
    generated: list[str] = []
    skipped: list[str] = []
    updated: list[str] = []
    warnings: list[str] = []

    for svc in registry.all_services():
        if not svc.env_entries or not svc.env_file:
            continue
        rel = str(svc.directory / svc.env_file)
        result = generate(svc, root, force=force, local_auth=registry.local_auth)
        if result is GenerateResult.CREATED:
            print(f"  ✔ Generated {rel}")
            generated.append(rel)
        elif result is GenerateResult.UPDATED:
            print(f"  ✔ Updated {rel} (added missing keys)")
            updated.append(rel)
        else:
            print(f"  ⏭ Skipped {rel} (already exists)")
            skipped.append(rel)

        if align_local_auth(svc, root, local_auth=registry.local_auth):
            if rel not in updated:
                print(f"  ✔ Updated {rel} (aligned local_auth_enabled)")
                updated.append(rel)

        placeholders, _ = check_unresolved(svc, root)
        for key in placeholders:
            warnings.append(f"  ⚠ {svc.name}: {rel}  {key} is still a placeholder!")

    return generated, skipped, updated, warnings

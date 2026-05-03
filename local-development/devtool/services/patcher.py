"""Application service: source-file patching."""

from __future__ import annotations

from pathlib import Path

from devtool.domain.models import Service
from devtool.domain.registry import Registry


def apply_patches(service: Service, root: Path) -> list[str]:
    """Apply all patch specs for *service*.

    Returns the list of files that were actually modified.
    """
    modified: list[str] = []
    for spec in service.patches:
        abs_path = root / spec.file
        if not abs_path.exists():
            print(f"  ⚠ WARNING: {spec.file} not found — skipping patch")
            continue

        original = abs_path.read_text()
        patched = original.replace(spec.find, spec.replace)

        if patched == original:
            if spec.find not in original and spec.replace not in original:
                print(
                    f"  ⚠ WARNING: pattern not found in {spec.file} "
                    f"— patch may be stale"
                )
            else:
                print(f"  ✔ {spec.file} already patched")
        else:
            abs_path.write_text(patched)
            print(f"  📝 Patched {spec.file}")
            modified.append(str(spec.file))

    return modified


def apply_all(registry: Registry, root: Path) -> list[str]:
    """Apply patches for every service.  Returns all modified file paths."""
    all_modified: list[str] = []
    for svc in registry.all_services():
        if svc.patches:
            all_modified.extend(apply_patches(svc, root))
    return all_modified


def revert_patches(service: Service, root: Path) -> list[str]:
    """Revert all patch specs for *service* (swap find↔replace).

    Returns the list of files that were actually modified.
    """
    modified: list[str] = []
    for spec in service.patches:
        abs_path = root / spec.file
        if not abs_path.exists():
            continue

        original = abs_path.read_text()
        reverted = original.replace(spec.replace, spec.find)

        if reverted != original:
            abs_path.write_text(reverted)
            print(f"  ↩ Reverted {spec.file}")
            modified.append(str(spec.file))
        else:
            print(f"  ✔ {spec.file} already clean")

    return modified


def revert_all(registry: Registry, root: Path) -> list[str]:
    """Revert patches for every service.  Returns all modified file paths."""
    all_modified: list[str] = []
    for svc in registry.all_services():
        if svc.patches:
            all_modified.extend(revert_patches(svc, root))
    return all_modified

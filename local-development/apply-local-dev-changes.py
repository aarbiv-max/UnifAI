#!/usr/bin/env python3
"""
Script to apply local development configuration changes.
Modifies configuration files so all services can run side-by-side on localhost.

Port layout after patching:
  RAG           → 13457  (changed from 13456 to avoid SSO collision)
  UI (Vite)     → 5000   (changed from 5173)

Flags:
  --setup-venv              Create virtual environments, then apply changes
  --setup-venv-only         Create virtual environments only (skip .env + patches)
  --service <name>          With --setup-venv: create venv for one service only
                            (uses Python 3.11–3.13; override with UNIFAI_PYTHON)
  --force-env               Regenerate .env files even if they already exist
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = (
    Path(os.environ["UNIFAI_ROOT"]).expanduser().resolve()
    if os.environ.get("UNIFAI_ROOT", "").strip()
    else _SCRIPT_DIR.parent
)

sys.path.insert(0, str(_SCRIPT_DIR))

from config.local_dev_config import LocalDevConfig
from core.utils import write_env, run_command
from core.python_env import find_python
from core.registry import ServiceRegistry
from services import ALL_SERVICES


def _python_version_bounds(config: LocalDevConfig) -> tuple[tuple[int, int], tuple[int, int]]:
    parts_min = config.python_min.split(".")
    parts_max = config.python_max.split(".")
    return (
        (int(parts_min[0]), int(parts_min[1])),
        (int(parts_max[0]), int(parts_max[1])),
    )


def setup_venvs(registry: ServiceRegistry, config: LocalDevConfig, service_name: str | None = None) -> None:
    """Create virtual environments. If *service_name* is given, only that one."""
    python_min, python_max = _python_version_bounds(config)
    env_override = (os.environ.get("UNIFAI_PYTHON") or "").strip() or None
    python = find_python(python_min, python_max, env_override=env_override)
    ver = subprocess.check_output([python, "--version"], text=True).strip()

    log_file = Path(f"/tmp/unifai-venv-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log")
    print(f"  Install output logged to: {log_file}\n")

    if service_name:
        svc = registry.get(service_name)
        targets = [svc]
        print(f"\n📦 Setting up virtual environment for '{service_name}' with {ver} ({python})\n")
    else:
        targets = registry.primary_services()
        print(f"\n📦 Setting up virtual environments with {ver} ({python})\n")

    for svc in targets:
        print(f"  ── {svc.name} ({svc.directory}) ──")
        cmds = svc.venv_build_commands(python)
        if not cmds:
            print(f"    ⚠  No build commands for {svc.name} — skipping.")
        else:
            for cmd in cmds:
                run_command(cmd, cwd=svc.absolute_directory, log_file=log_file)
            print(f"    ✔ {svc.venv_success_message}")
        print()

    print("✅ Virtual environment(s) created.\n")


def apply_changes(registry: ServiceRegistry, root: Path, *, force_env: bool = False) -> None:
    """Generate .env files and apply source-file patches for all services."""
    print(f"🔧 Applying local development configuration… (repo: {root})")
    modified: list[str] = []
    generated: list[str] = []
    skipped: list[str] = []

    for svc in registry.all():
        for spec in svc.patch_specs():
            abs_path = root / spec.file
            content = abs_path.read_text()
            content = content.replace(spec.find, spec.replace)
            abs_path.write_text(content)
            print(f"  📝 Updating {spec.file}...")
            modified.append(str(spec.file))

        entries = svc.env_entries()
        env_path = svc.env_file_path
        if entries and env_path:
            rel = str(env_path.relative_to(root))
            if write_env(env_path, entries, force=force_env):
                print(f"  ✔ Generating {rel}...")
                generated.append(rel)
            else:
                print(f"  ⏭  Skipping {rel} (already exists)")
                skipped.append(rel)

    print("\n✅ Local development configuration applied successfully!")
    if generated:
        print("\nGenerated .env files (gitignored):")
        for f in generated:
            print(f"  - {f}")
    if skipped:
        print("\nPreserved existing .env files (use --force-env to regenerate):")
        for f in skipped:
            print(f"  - {f}")
    if modified:
        print("\nPatched source files:")
        for f in modified:
            print(f"  - {f}")

    has_messages = False
    for svc in registry.all():
        msg = svc.post_apply_message()
        if msg:
            print(f"\n{msg}")
            has_messages = True

    if not has_messages:
        print(
            "\n💡 Tip: To revert source-file patches run 'git checkout' on the patched files."
            "\n   The .env files are gitignored and can be safely deleted."
        )


def _print_help() -> None:
    print("Usage: apply-local-dev-changes.py [--setup-venv] [--setup-venv-only] [--service <name>] [--force-env]")
    print("")
    print("Generates .env files and patches source files for local development.")
    print("")
    print("  On first run, .env files are created with default/placeholder values.")
    print("  On subsequent runs, existing .env files are preserved (source patches")
    print("  are always re-applied). Use --force-env to regenerate .env files.")
    print("")
    print("Flags:")
    print("  --setup-venv             Create virtual environments, then apply changes")
    print("  --setup-venv-only        Create virtual environments only (skip .env generation + patches)")
    print("  --service <name>         With --setup-venv: create venv for one service only")
    print("                           (uses Python 3.11–3.13; override with UNIFAI_PYTHON)")
    print("  --force-env              Regenerate .env files even if they already exist")
    print("")
    print("Services: backend, rag, multi-agent, sso, ui, celery-worker, temporal-worker")


if __name__ == "__main__":
    try:
        args = sys.argv[1:]
        do_setup_venv = "--setup-venv" in args or "--setup-venv-only" in args
        force_env = "--force-env" in args
        show_help = "-h" in args or "--help" in args

        service_name: str | None = None
        if "--service" in args:
            idx = args.index("--service")
            if idx + 1 >= len(args):
                print("❌ --service requires a service name.", file=sys.stderr)
                sys.exit(1)
            service_name = args[idx + 1]

        if show_help:
            _print_help()
            sys.exit(0)

        root = _REPO_ROOT
        config = LocalDevConfig()
        registry = ServiceRegistry(root, config, ALL_SERVICES)

        if do_setup_venv:
            setup_venvs(registry, config, service_name)
            if "--setup-venv-only" not in args:
                apply_changes(registry, root, force_env=force_env)
        else:
            apply_changes(registry, root, force_env=force_env)
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

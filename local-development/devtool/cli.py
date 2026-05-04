"""Driving adapter: CLI that parses args and dispatches to the orchestrator."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import typer

# -- Root app ----------------------------------------------------------------

app = typer.Typer(
    name="unifai-dev",
    help="UnifAI local development tool",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

# -- Sub-apps ----------------------------------------------------------------

infra_app = typer.Typer(
    name="infra",
    help="Manage infrastructure containers",
    no_args_is_help=True,
)
app.add_typer(infra_app)

venv_app = typer.Typer(
    name="venv",
    help="Manage virtual environments",
    no_args_is_help=True,
)
app.add_typer(venv_app)

env_app = typer.Typer(
    name="env",
    help="Manage .env files",
    no_args_is_help=True,
)
app.add_typer(env_app)

patch_app = typer.Typer(
    name="patch",
    help="Manage source-file patches",
    no_args_is_help=True,
)
app.add_typer(patch_app)


# -- Helpers (unchanged) -----------------------------------------------------

def _parse_window_specs(
    raw: list[str] | None,
) -> list[tuple[str | None, list[str]]] | None:
    """Parse --window values into ``[(name_or_None, [svc_names]), ...]``."""
    if not raw:
        return None
    specs: list[tuple[str | None, list[str]]] = []
    for entry in raw:
        if "=" in entry:
            name, rest = entry.split("=", 1)
            names = [n.strip() for n in rest.split(",") if n.strip()]
            specs.append((name.strip(), names))
        else:
            names = [n.strip() for n in entry.split(",") if n.strip()]
            specs.append((None, names))
    return specs


def _resolve_root() -> Path:
    """Find the repo root (parent of local-development/)."""
    script_dir = Path(__file__).resolve().parent.parent
    root = script_dir.parent
    if not (root / "rag").is_dir() or not (root / "ui").is_dir():
        alt = os.environ.get("UNIFAI_ROOT", "").strip()
        if alt:
            return Path(alt).expanduser().resolve()
        print(
            f"❌ Cannot find UnifAI repo structure at {root}.\n"
            f"   Set UNIFAI_ROOT or run from the repo root.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return root


def _create_orchestrator(*, fg: bool = False):
    """Wire up adapters and return an Orchestrator."""
    from devtool.domain.registry import Registry
    from devtool.adapters.container_base import detect_runtime
    from devtool.adapters.tmux import TmuxSessionManager
    from devtool.adapters.foreground import ForegroundSessionManager
    from devtool.adapters.venv import LocalVenvManager
    from devtool.services.orchestrator import Orchestrator

    root = _resolve_root()
    registry = Registry()
    runtime = detect_runtime()
    session = ForegroundSessionManager() if fg else TmuxSessionManager()
    venv_mgr = LocalVenvManager()

    return Orchestrator(
        registry=registry,
        root=root,
        container_runtime=runtime,
        session_manager=session,
        venv_manager=venv_mgr,
    )


# -- Top-level commands ------------------------------------------------------

@app.command()
def start(
    targets: Optional[list[str]] = typer.Argument(
        None, help="Service and/or group names (default: all)",
    ),
    fg: bool = typer.Option(False, "--fg", help="Foreground single service"),
    setup_venv: bool = typer.Option(False, "--setup-venv", help="Create venvs first"),
    window: Optional[list[str]] = typer.Option(
        None, "--window",
        help="Group services into a tmux window (repeatable). "
             "Format: [name=]svc1,svc2,...",
    ),
):
    """Start services."""
    orch = _create_orchestrator(fg=fg)
    window_specs = _parse_window_specs(window)
    orch.start(
        targets=targets or None,
        fg=fg,
        setup_venv=setup_venv,
        window_specs=window_specs,
    )


@app.command()
def shell(service: str = typer.Argument(..., help="Service name")):
    """Open a shell in a service's context."""
    orch = _create_orchestrator()
    orch.shell(service)


@app.command(
    "exec",
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)
def exec_cmd(
    ctx: typer.Context,
    service: str = typer.Argument(..., help="Service name"),
):
    """Run a command in a service's context."""
    if not ctx.args:
        print("Usage: unifai-dev exec <service> <command...>")
        raise SystemExit(1)
    orch = _create_orchestrator()
    orch.exec_in_context(service, ctx.args)


@app.command()
def attach(service: str = typer.Argument(..., help="Service name")):
    """Jump to a service's tmux pane."""
    orch = _create_orchestrator()
    orch.attach(service)


@app.command()
def stop():
    """Stop the tmux session."""
    orch = _create_orchestrator()
    orch.stop()


@app.command()
def restart(
    services: Optional[list[str]] = typer.Argument(
        None, help="Service and/or group names",
    ),
    failed: bool = typer.Option(False, "--failed", help="Auto-restart all broken services"),
):
    """Dependency-aware restart."""
    orch = _create_orchestrator()
    orch.restart(targets=services or None, failed=failed)


@app.command()
def status():
    """Health dashboard."""
    orch = _create_orchestrator()
    orch.status()


@app.command()
def logs(
    service: str = typer.Argument(..., help="Service name"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Tail the log"),
):
    """View service logs."""
    orch = _create_orchestrator()
    orch.logs(service, follow=follow)


@app.command()
def doctor():
    """Full diagnostic."""
    orch = _create_orchestrator()
    orch.doctor()


@app.command()
def init(
    non_interactive: bool = typer.Option(
        False, "--non-interactive",
        help="Skip interactive prompts (warn about placeholders instead)",
    ),
):
    """First-time setup."""
    orch = _create_orchestrator()
    orch.init(non_interactive=non_interactive)


@app.command()
def clean(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be removed"),
    logs: bool = typer.Option(False, "--logs", help="Only clean log files"),
    venvs: bool = typer.Option(False, "--venvs", help="Only clean virtual environments"),
    containers: bool = typer.Option(False, "--containers", help="Only clean stopped containers"),
):
    """Remove stale resources."""
    orch = _create_orchestrator()
    has_filter = logs or venvs or containers
    orch.clean(
        dry_run=dry_run,
        clean_logs=logs or not has_filter,
        clean_venvs=venvs,
        clean_containers=containers or not has_filter,
    )


@app.command()
def destroy():
    """Kill everything."""
    orch = _create_orchestrator()
    orch.destroy()


# -- infra subcommands -------------------------------------------------------

@infra_app.command("start")
def infra_start(
    containers: Optional[list[str]] = typer.Argument(None, help="Container names"),
    for_service: Optional[str] = typer.Option(
        None, "--for", help="Only what a service needs",
    ),
):
    """Start infrastructure containers."""
    orch = _create_orchestrator()
    orch.infra_start(targets=containers or None, for_service=for_service)


@infra_app.command("stop")
def infra_stop():
    """Stop all infrastructure containers."""
    orch = _create_orchestrator()
    orch.infra_stop()


@infra_app.command("status")
def infra_status():
    """Container status."""
    orch = _create_orchestrator()
    orch.infra_status()


@infra_app.command("logs")
def infra_logs(
    component: str = typer.Argument(..., help="Infrastructure component name"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Tail the log"),
):
    """View container logs."""
    orch = _create_orchestrator()
    orch.infra_logs(component, follow=follow)


@infra_app.command("reset")
def infra_reset(
    components: Optional[list[str]] = typer.Argument(None, help="Component names"),
):
    """Reset containers (stop, remove, recreate)."""
    orch = _create_orchestrator()
    orch.infra_reset(targets=components or None)


# -- venv subcommands --------------------------------------------------------

@venv_app.command("setup")
def venv_setup(
    service: Optional[str] = typer.Argument(None, help="Service name"),
    force: bool = typer.Option(False, "--force", help="Delete and recreate existing venvs"),
):
    """Create virtual environment(s)."""
    orch = _create_orchestrator()
    orch.venv_setup(service_name=service, force=force)


@venv_app.command("sync")
def venv_sync(
    service: Optional[str] = typer.Argument(None, help="Service name"),
):
    """Update dependencies in existing venv(s)."""
    orch = _create_orchestrator()
    orch.venv_sync(service_name=service)


@venv_app.command("check")
def venv_check():
    """Verify Python versions match."""
    orch = _create_orchestrator()
    orch.venv_check()


# -- env subcommands ---------------------------------------------------------

@env_app.command("generate")
def env_generate(
    force: bool = typer.Option(False, "--force", help="Overwrite existing .env files"),
):
    """Create/regenerate .env files."""
    orch = _create_orchestrator()
    orch.env_generate(force=force)


@env_app.command("show")
def env_show(
    service: str = typer.Argument(..., help="Service name"),
):
    """Print env config for a service."""
    orch = _create_orchestrator()
    orch.env_show(service)


# -- patch subcommands -------------------------------------------------------

@patch_app.command("apply")
def patch_apply():
    """Apply patches to source files."""
    orch = _create_orchestrator()
    orch.patch_apply()


@patch_app.command("revert")
def patch_revert():
    """Revert previously applied patches."""
    orch = _create_orchestrator()
    orch.patch_revert()

"""Driving adapter: CLI that parses args and dispatches to the orchestrator."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="unifai-dev",
        description="UnifAI local development tool",
    )
    sub = parser.add_subparsers(dest="command")

    # -- start ---------------------------------------------------------------
    p_start = sub.add_parser("start", help="Start services")
    p_start.add_argument(
        "targets", nargs="*", default=None,
        help="Service and/or group names (default: all)",
    )
    p_start.add_argument("--fg", action="store_true", help="Foreground single service")
    p_start.add_argument("--setup-venv", action="store_true", help="Create venvs first")
    p_start.add_argument(
        "--window", action="append", default=None,
        metavar="[name=]svc1,svc2,...",
        help="Group services into a tmux window (repeatable). "
             "Each --window creates a new window with the listed services as panes. "
             "Optionally prefix with 'name=' to name the window.",
    )

    # -- shell ---------------------------------------------------------------
    p_shell = sub.add_parser("shell", help="Open a shell in a service's context")
    p_shell.add_argument("service", help="Service name")

    # -- exec ----------------------------------------------------------------
    p_exec = sub.add_parser("exec", help="Run a command in a service's context")
    p_exec.add_argument("service", help="Service name")
    p_exec.add_argument("exec_command", nargs=argparse.REMAINDER, help="Command to run")

    # -- attach --------------------------------------------------------------
    p_attach = sub.add_parser("attach", help="Jump to a service's tmux pane")
    p_attach.add_argument("service", help="Service name")

    # -- stop ----------------------------------------------------------------
    sub.add_parser("stop", help="Stop the tmux session")

    # -- restart -------------------------------------------------------------
    p_restart = sub.add_parser("restart", help="Dependency-aware restart")
    p_restart.add_argument(
        "services", nargs="*", default=None,
        help="Service and/or group names",
    )
    p_restart.add_argument("--failed", action="store_true", help="Auto-restart all broken services")

    # -- status --------------------------------------------------------------
    sub.add_parser("status", help="Health dashboard")

    # -- logs ----------------------------------------------------------------
    p_logs = sub.add_parser("logs", help="View service logs")
    p_logs.add_argument("service", help="Service name")
    p_logs.add_argument("--follow", "-f", action="store_true", help="Tail the log")

    # -- doctor --------------------------------------------------------------
    sub.add_parser("doctor", help="Full diagnostic")

    # -- infra ---------------------------------------------------------------
    p_infra = sub.add_parser("infra", help="Manage infrastructure containers")
    infra_sub = p_infra.add_subparsers(dest="infra_command")

    p_infra_start = infra_sub.add_parser("start", help="Start containers")
    p_infra_start.add_argument("containers", nargs="*", default=None)
    p_infra_start.add_argument("--for", dest="for_service", help="Only what a service needs")

    infra_sub.add_parser("stop", help="Stop all containers")
    infra_sub.add_parser("status", help="Container status")

    p_infra_logs = infra_sub.add_parser("logs", help="View container logs")
    p_infra_logs.add_argument("component", help="Infrastructure component name")
    p_infra_logs.add_argument("--follow", "-f", action="store_true", help="Tail the log")

    p_infra_reset = infra_sub.add_parser("reset", help="Reset containers (stop, remove, recreate)")
    p_infra_reset.add_argument("components", nargs="*", default=None)

    # -- venv ----------------------------------------------------------------
    p_venv = sub.add_parser("venv", help="Manage virtual environments")
    venv_sub = p_venv.add_subparsers(dest="venv_command")

    p_venv_setup = venv_sub.add_parser("setup", help="Create venv(s)")
    p_venv_setup.add_argument("service", nargs="?", default=None)
    p_venv_setup.add_argument("--force", action="store_true", help="Delete and recreate existing venvs")

    venv_sub.add_parser("check", help="Verify Python versions match")

    # -- env -----------------------------------------------------------------
    p_env = sub.add_parser("env", help="Manage .env files")
    env_sub = p_env.add_subparsers(dest="env_command")

    p_env_gen = env_sub.add_parser("generate", help="Create/regenerate .env files")
    p_env_gen.add_argument("--force", action="store_true")

    p_env_show = env_sub.add_parser("show", help="Print env config for a service")
    p_env_show.add_argument("service", help="Service name")

    # -- patch ---------------------------------------------------------------
    p_patch = sub.add_parser("patch", help="Manage source-file patches")
    patch_sub = p_patch.add_subparsers(dest="patch_command")
    patch_sub.add_parser("apply", help="Apply patches to source files")
    patch_sub.add_parser("revert", help="Revert previously applied patches")

    # -- init ----------------------------------------------------------------
    p_init = sub.add_parser("init", help="First-time setup wizard")
    p_init.add_argument(
        "--non-interactive", action="store_true",
        help="Skip interactive prompts (warn about placeholders instead)",
    )

    # -- clean ---------------------------------------------------------------
    p_clean = sub.add_parser("clean", help="Remove stale resources")
    p_clean.add_argument("--dry-run", action="store_true", help="Show what would be removed")
    p_clean.add_argument("--logs", action="store_true", help="Only clean log files")
    p_clean.add_argument("--venvs", action="store_true", help="Only clean virtual environments")
    p_clean.add_argument("--containers", action="store_true", help="Only clean stopped containers")

    # -- destroy -------------------------------------------------------------
    sub.add_parser("destroy", help="Kill everything")

    return parser


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


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        raise SystemExit(0)

    try:
        _dispatch(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"\n❌ Error: {exc}", file=sys.stderr)
        raise SystemExit(1)


def _dispatch(args: argparse.Namespace) -> None:
    cmd = args.command

    if cmd == "start":
        orch = _create_orchestrator(fg=args.fg)
        window_specs = _parse_window_specs(args.window)
        orch.start(
            targets=args.targets or None,
            fg=args.fg,
            setup_venv=args.setup_venv,
            window_specs=window_specs,
        )

    elif cmd == "shell":
        orch = _create_orchestrator()
        orch.shell(args.service)

    elif cmd == "exec":
        orch = _create_orchestrator()
        if not args.exec_command:
            print("Usage: unifai-dev exec <service> <command...>")
            raise SystemExit(1)
        orch.exec_in_context(args.service, args.exec_command)

    elif cmd == "attach":
        orch = _create_orchestrator()
        orch.attach(args.service)

    elif cmd == "stop":
        orch = _create_orchestrator()
        orch.stop()

    elif cmd == "restart":
        orch = _create_orchestrator()
        orch.restart(targets=args.services or None, failed=args.failed)

    elif cmd == "status":
        orch = _create_orchestrator()
        orch.status()

    elif cmd == "logs":
        orch = _create_orchestrator()
        orch.logs(args.service, follow=args.follow)

    elif cmd == "doctor":
        orch = _create_orchestrator()
        orch.doctor()

    elif cmd == "infra":
        orch = _create_orchestrator()
        if args.infra_command == "start":
            orch.infra_start(
                targets=args.containers or None,
                for_service=args.for_service,
            )
        elif args.infra_command == "stop":
            orch.infra_stop()
        elif args.infra_command == "status":
            orch.infra_status()
        elif args.infra_command == "logs":
            orch.infra_logs(args.component, follow=args.follow)
        elif args.infra_command == "reset":
            orch.infra_reset(targets=args.components or None)
        else:
            print("Usage: unifai-dev infra {start|stop|status|logs|reset}")

    elif cmd == "venv":
        orch = _create_orchestrator()
        if args.venv_command == "setup":
            orch.venv_setup(service_name=args.service, force=args.force)
        elif args.venv_command == "check":
            orch.venv_check()
        else:
            print("Usage: unifai-dev venv {setup|check}")

    elif cmd == "env":
        orch = _create_orchestrator()
        if args.env_command == "generate":
            orch.env_generate(force=args.force)
        elif args.env_command == "show":
            orch.env_show(args.service)
        else:
            print("Usage: unifai-dev env {generate|show}")

    elif cmd == "patch":
        orch = _create_orchestrator()
        if args.patch_command == "apply":
            orch.patch_apply()
        elif args.patch_command == "revert":
            orch.patch_revert()
        else:
            print("Usage: unifai-dev patch {apply|revert}")

    elif cmd == "init":
        orch = _create_orchestrator()
        orch.init(non_interactive=args.non_interactive)

    elif cmd == "clean":
        orch = _create_orchestrator()
        has_filter = args.logs or args.venvs or args.containers
        orch.clean(
            dry_run=args.dry_run,
            clean_logs=args.logs or not has_filter,
            clean_venvs=args.venvs,
            clean_containers=args.containers or not has_filter,
        )

    elif cmd == "destroy":
        orch = _create_orchestrator()
        orch.destroy()

"""Application service: orchestrator — composes ports for start/stop flows."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from devtool.domain.models import Service, ServiceType, WindowLayout
from devtool.domain.registry import Registry
from devtool.ports.container_runtime import ContainerRuntime
from devtool.ports.session_manager import SessionManager
from devtool.ports.venv_manager import VenvManager
from devtool.services import env_generator, patcher, python_detector

SESSION_NAME = "unifai-dev"


class Orchestrator:

    def __init__(
        self,
        registry: Registry,
        root: Path,
        container_runtime: ContainerRuntime,
        session_manager: SessionManager,
        venv_manager: VenvManager,
    ) -> None:
        self._registry = registry
        self._root = root
        self._runtime = container_runtime
        self._session = session_manager
        self._venv = venv_manager

    # -- start ---------------------------------------------------------------

    def start(
        self,
        targets: list[str] | None = None,
        *,
        fg: bool = False,
        setup_venv: bool = False,
        window_specs: list[tuple[str | None, list[str]]] | None = None,
    ) -> None:
        if not targets and not window_specs:
            targets = ["all"]

        if window_specs:
            all_names: list[str] = list(targets or [])
            for _, names in window_specs:
                all_names.extend(names)
            services = self._registry.resolve_services(all_names)
        else:
            services = self._registry.resolve_services(targets or ["all"])

        self._validate_start(services, fg=fg)

        python, python_minor = self._detect_python()

        # 1. Infrastructure
        infra = self._registry.infra_for_services(services)
        if infra:
            log_dir = self._registry.log_dir
            log_dir.mkdir(parents=True, exist_ok=True)
            self._runtime.set_log_file(log_dir / "infra.log")
            print(f"\nUsing container runtime: {self._runtime.runtime_name}")
            print(f"\nStarting infrastructure: {', '.join(c.name for c in infra)}\n")
            for comp in infra:
                self._runtime.ensure_running(comp)
            print("\n✅ Infrastructure ready.\n")
            time.sleep(1)

        # 2. Venv setup (optional)
        if setup_venv:
            print("📦 Setting up virtual environments…\n")
            log_dir = self._registry.log_dir
            log_dir.mkdir(parents=True, exist_ok=True)
            venv_errors: list[str] = []
            for svc in services:
                if svc.is_primary:
                    try:
                        self._venv.create(svc, python, self._root, log_dir=log_dir)
                        print(f"  ✔ {svc.name}")
                    except RuntimeError as exc:
                        print(f"  ✖ {svc.name}: {exc}")
                        venv_errors.append(svc.name)
            if venv_errors:
                print(f"\n⚠ Venv setup failed for: {', '.join(venv_errors)}")
                print(f"  Check logs in {log_dir}/")
            print()

        # 3. Env generation
        print("🔧 Generating .env files…")
        _generated, _skipped, env_warnings = env_generator.generate_all(
            self._registry, self._root,
        )
        for w in env_warnings:
            print(w)
        print()

        # 4. Source patches
        print("🔧 Applying source patches…")
        modified = patcher.apply_all(self._registry, self._root)
        if modified:
            print(f"\n  Patched: {', '.join(modified)}")
        print()

        # 5. Verify venvs
        for svc in services:
            if svc.is_primary and svc.type is ServiceType.PYTHON:
                self._venv.verify(svc, python_minor, self._root)

        # 6. Kill ports
        for svc in services:
            if svc.port:
                self._kill_port(svc.port)

        # 7. Build shell commands
        commands = self._build_commands(services, python_minor)

        # 8. Build window layout
        if window_specs:
            layout = self._build_custom_layout(
                window_specs, targets or [], services,
            )
        else:
            layout = self._build_default_layout(services)

        # 9. Launch
        print(f"Using Python: {python}")
        self._session.launch(
            SESSION_NAME, layout, commands, self._registry.log_dir,
        )

        if not fg:
            self._print_summary(services, infra)
            self._session.attach(SESSION_NAME)

    # -- attach --------------------------------------------------------------

    def attach(self, service_name: str) -> None:
        """Jump to the tmux pane running a specific service."""
        if not self._session.is_running(SESSION_NAME):
            print(f"No session '{SESSION_NAME}' running. Start services first.")
            return

        svc = self._registry.get_service(service_name)
        pane_contents = self._session.pane_contents(SESSION_NAME)

        from devtool.services.health_checker import match_panes_to_services
        mapping = match_panes_to_services([svc], pane_contents)

        pane_ref = mapping.get(svc.name)
        if not pane_ref:
            print(f"Could not find a tmux pane for '{svc.name}'.")
            return

        pane_target = f"{SESSION_NAME}:{pane_ref}"
        subprocess.run(
            ["tmux", "select-window", "-t", pane_target.rsplit(".", 1)[0]],
            check=False,
        )
        subprocess.run(
            ["tmux", "select-pane", "-t", pane_target],
            check=False,
        )
        self._session.attach(SESSION_NAME)

    # -- shell / exec --------------------------------------------------------

    def shell(self, service_name: str) -> None:
        """Drop into an interactive shell with the service's context loaded."""
        svc = self._registry.get_service(service_name)
        _, python_minor = self._detect_python()
        context = self._build_context_command(svc, python_minor)
        shell_cmd = f"{context} && exec bash"
        print(f"\n🐚 Entering {svc.name} environment…\n")
        os.execvp("/bin/bash", ["/bin/bash", "-c", shell_cmd])

    def exec_in_context(self, service_name: str, command: list[str]) -> None:
        """Run *command* inside the service's context, then exit."""
        svc = self._registry.get_service(service_name)
        _, python_minor = self._detect_python()
        context = self._build_context_command(svc, python_minor)
        user_cmd = " ".join(command)
        shell_cmd = f"{context} && {user_cmd}"
        os.execvp("/bin/bash", ["/bin/bash", "-c", shell_cmd])

    # -- stop / destroy ------------------------------------------------------

    def stop(self) -> None:
        if self._session.is_running(SESSION_NAME):
            self._session.kill_session(SESSION_NAME)
            print(f"Session '{SESSION_NAME}' destroyed.")
        else:
            print(f"No session '{SESSION_NAME}' found.")

    def destroy(self) -> None:
        if self._session.is_running(SESSION_NAME):
            print("Gracefully stopping services…")
            self._session.graceful_stop(SESSION_NAME)
            print("Services stopped.")
        else:
            print(f"No session '{SESSION_NAME}' found.")
        print("\nStopping infrastructure…")
        self._runtime.set_log_file(self._registry.log_dir / "infra.log")
        self._runtime.stop_all(self._registry.all_infra())

    # -- infra subcommands ---------------------------------------------------

    def infra_start(
        self, targets: list[str] | None = None, *, for_service: str | None = None,
    ) -> None:
        self._runtime.set_log_file(self._registry.log_dir / "infra.log")
        print(f"Using container runtime: {self._runtime.runtime_name}\n")

        if for_service:
            svc = self._registry.get_service(for_service)
            components = self._registry.infra_for_services([svc])
            if not components:
                print(f"ℹ  Service '{for_service}' needs no infrastructure.")
                return
        elif targets:
            components = [self._registry.get_infra(t) for t in targets]
        else:
            components = self._registry.all_infra()

        print(f"Starting infrastructure: {', '.join(c.name for c in components)}\n")
        for comp in components:
            self._runtime.ensure_running(comp)
        print("\n✅ Infrastructure ready.")

    def infra_stop(self) -> None:
        self._runtime.set_log_file(self._registry.log_dir / "infra.log")
        self._runtime.stop_all(self._registry.all_infra())

    def infra_logs(
        self, component_name: str, *, follow: bool = False,
    ) -> None:
        comp = self._registry.get_infra(component_name)
        self._runtime.logs(comp, follow=follow)

    def infra_reset(self, targets: list[str] | None = None) -> None:
        self._runtime.set_log_file(self._registry.log_dir / "infra.log")
        if targets:
            components = [self._registry.get_infra(t) for t in targets]
        else:
            components = self._registry.all_infra()

        print(f"Resetting: {', '.join(c.label for c in components)}\n")
        for comp in components:
            self._runtime.reset(comp)
        print("\n✅ Infrastructure reset complete.")

    def infra_status(self) -> None:
        from devtool.domain.models import ContainerStatus

        print("Infrastructure container status:")
        for comp in self._registry.all_infra():
            st = self._runtime.status(comp)
            if st is ContainerStatus.RUNNING:
                icon = "✔"
                label = "running"
            elif st is ContainerStatus.STOPPED:
                icon = "⏹"
                label = "stopped"
            else:
                icon = "✖"
                label = "not created"
            print(f"  {icon} {comp.label} ({comp.name}) — {label}")

    # -- venv subcommands ----------------------------------------------------

    def venv_setup(self, service_name: str | None = None, *, force: bool = False) -> None:
        python, _ = self._detect_python()
        if service_name:
            svc = self._registry.get_service(service_name)
            targets = [svc]
        else:
            targets = self._registry.primary_services()

        log_dir = self._registry.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        errors: list[str] = []
        skipped: list[str] = []

        print(f"📦 Setting up virtual environments with {python}\n")
        for svc in targets:
            try:
                existed = self._venv.exists(svc, self._root)
                self._venv.create(svc, python, self._root, log_dir=log_dir, force=force)
                if existed and not force:
                    print(f"  ⏭ {svc.name} (already exists, use --force to recreate)")
                    skipped.append(svc.name)
                else:
                    print(f"  ✔ {svc.name}")
            except RuntimeError as exc:
                print(f"  ✖ {svc.name}: {exc}")
                errors.append(svc.name)

        if errors:
            print(f"\n⚠ Venv setup failed for: {', '.join(errors)}")
            print(f"  Check logs in {log_dir}/")
        elif skipped and not force:
            print("\n✅ Nothing to do (use --force to recreate).")
        else:
            print("\n✅ Virtual environment(s) created.")

    def venv_check(self) -> None:
        _, python_minor = self._detect_python()
        errors: list[str] = []
        for svc in self._registry.primary_services():
            if svc.type is not ServiceType.PYTHON:
                continue
            try:
                self._venv.verify(svc, python_minor, self._root)
                print(f"  ✔ {svc.name}: OK")
            except RuntimeError as exc:
                print(f"  ✖ {svc.name}: {exc}")
                errors.append(svc.name)
        if errors:
            raise SystemExit(1)

    # -- env subcommands -----------------------------------------------------

    def env_generate(self, *, force: bool = False) -> None:
        print("🔧 Generating .env files…")
        generated, skipped, warnings = env_generator.generate_all(
            self._registry, self._root, force=force,
        )
        if generated:
            print(f"\nGenerated: {', '.join(generated)}")
        if skipped:
            print(
                f"\nPreserved existing (use --force to regenerate): "
                f"{', '.join(skipped)}"
            )
        for w in warnings:
            print(w)

    def env_show(self, service_name: str) -> None:
        svc = self._registry.get_service(service_name)
        env_generator.show(svc, self._root)

    # -- patch subcommand ----------------------------------------------------

    def patch_apply(self) -> None:
        print("🔧 Applying source patches…")
        modified = patcher.apply_all(self._registry, self._root)
        if modified:
            print(f"\nPatched: {', '.join(modified)}")
            print("\n💡 Tip: run 'unifai-dev patch revert' to undo these patches.")

    def patch_revert(self) -> None:
        print("↩ Reverting source patches…")
        modified = patcher.revert_all(self._registry, self._root)
        if modified:
            print(f"\nReverted: {', '.join(modified)}")
        else:
            print("\nNothing to revert — all files are already clean.")

    # -- logs ----------------------------------------------------------------

    def logs(self, service_name: str, *, follow: bool = False) -> None:
        log_path = self._registry.log_dir / f"{service_name}.log"
        if not log_path.exists():
            print(f"No log file found at {log_path}")
            return

        if follow:
            subprocess.run(["tail", "-f", str(log_path)])
        else:
            print(log_path.read_text(), end="")

    # -- status / doctor -----------------------------------------------------

    def status(self) -> None:
        from devtool.services.health_checker import build_dashboard, render_dashboard

        infra, services, issues = build_dashboard(
            self._registry, self._runtime, self._session,
        )
        render_dashboard(infra, services, issues)

    def doctor(self) -> None:
        print("🩺 Running diagnostics…\n")

        # Python
        try:
            python, python_minor = self._detect_python()
            print(f"  ✔ Python: {python} ({python_minor})")
        except RuntimeError as exc:
            print(f"  ✖ Python: {exc}")

        # Container runtime
        print(f"  ✔ Container runtime: {self._runtime.runtime_name}")

        # Infra
        print()
        self.infra_status()

        # Venvs
        print("\nVirtual environments:")
        self.venv_check()

        # Env files
        print("\nEnvironment files:")
        for svc in self._registry.all_services():
            if svc.env_file:
                env_path = self._root / svc.directory / svc.env_file
                rel = env_path.relative_to(self._root)
                if env_path.exists():
                    print(f"  ✔ {svc.name}: {rel}")
                    placeholders = env_generator.check_placeholders(svc, self._root)
                    for key in placeholders:
                        print(f"  ⚠ {svc.name}: {rel}  {key} is still a placeholder!")
                else:
                    if svc.env_entries:
                        print(f"  ✖ {svc.name}: {rel} missing")
                        print(f"    💡 Tip: run 'unifai-dev env generate' to generate the .env file.")
                    else:
                        print(f"  ✔ {svc.name}: {rel} shouldn't exist")

        # Ports
        print("\nPort availability:")
        for svc in self._registry.all_services():
            if svc.port:
                in_use = self._is_port_in_use(svc.port)
                icon = "⚠ in use" if in_use else "✔ free"
                print(f"  {icon}: port {svc.port} ({svc.name})")

    # -- restart -------------------------------------------------------------

    def restart(self, targets: list[str] | None = None, *, failed: bool = False) -> None:
        from devtool.services.recovery import Recovery

        recovery = Recovery(self._registry, self._runtime, self._session, self._venv)

        if failed:
            recovery.restart_failed(self._root)
        elif targets:
            services = self._registry.resolve_services(targets)
            for svc in services:
                recovery.restart_service(svc.name, self._root)
        else:
            print("Specify service/group names or use --failed.")

    # -- init ----------------------------------------------------------------

    def init(self, *, non_interactive: bool = False) -> None:
        """First-time setup wizard: prerequisites, infra, venvs, env, patches."""
        print("🚀 UnifAI first-time setup\n")

        # 1. Prerequisites
        print("1/6  Checking prerequisites…")
        try:
            python, python_minor = self._detect_python()
            print(f"  ✔ Python: {python} ({python_minor})")
        except RuntimeError as exc:
            print(f"  ✖ Python: {exc}")
            raise SystemExit(1)

        print(f"  ✔ Container runtime: {self._runtime.runtime_name}")

        if not shutil.which("tmux"):
            print("  ✖ tmux not found — install tmux to use multi-service mode.")
        else:
            print("  ✔ tmux available")
        print()

        # 2. Infrastructure
        print("2/6  Starting infrastructure…")
        self.infra_start()
        print()

        # 3. Venvs
        print("3/6  Setting up virtual environments…")
        self.venv_setup()
        print()

        # 4. Env generation
        print("4/6  Generating .env files…")
        self.env_generate()
        print()

        # 5. Placeholder prompts
        print("5/6  Checking for placeholder values…")
        any_placeholders = False
        for svc in self._registry.all_services():
            placeholders = env_generator.check_placeholders(svc, self._root)
            if not placeholders:
                continue
            any_placeholders = True
            env_path = self._root / svc.directory / svc.env_file
            if non_interactive:
                for key in placeholders:
                    print(f"  ⚠ {svc.name}: {key} is still a placeholder")
            else:
                for key in placeholders:
                    value = input(f"  Enter value for {svc.name} / {key}: ").strip()
                    if value:
                        self._replace_placeholder(env_path, key, value)
                        print(f"    ✔ {key} updated")
                    else:
                        print(f"    ⏭ {key} skipped")
        if not any_placeholders:
            print("  ✔ No placeholders to fill.")
        print()

        # 6. Patches
        print("6/6  Applying source patches…")
        self.patch_apply()
        print()

        print("╔══════════════════════════════════════════════════════════════╗")
        print("║  Setup complete!                                            ║")
        print("║                                                             ║")
        print("║  Next steps:                                                ║")
        print("║    unifai-dev start         Start all services              ║")
        print("║    unifai-dev doctor        Verify everything is healthy    ║")
        print("╚══════════════════════════════════════════════════════════════╝")

    @staticmethod
    def _replace_placeholder(env_path: Path, key: str, new_value: str) -> None:
        """Rewrite a single key=<placeholder> line in an env file."""
        lines = env_path.read_text().splitlines(keepends=True)
        with open(env_path, "w") as f:
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith(f"{key}="):
                    f.write(f"{key}={new_value}\n")
                else:
                    f.write(line)

    # -- clean ---------------------------------------------------------------

    def clean(
        self,
        *,
        dry_run: bool = False,
        clean_logs: bool = True,
        clean_venvs: bool = False,
        clean_containers: bool = True,
    ) -> None:
        """Remove stale resources: log files, stopped containers, venvs."""
        from devtool.domain.models import ContainerStatus

        removed: list[str] = []

        # Logs
        if clean_logs:
            log_dir = self._registry.log_dir
            if log_dir.is_dir():
                for f in sorted(log_dir.iterdir()):
                    if f.is_file():
                        label = f"log: {f.name}"
                        if dry_run:
                            print(f"  (would remove) {label}")
                        else:
                            f.unlink()
                            print(f"  ✔ Removed {label}")
                        removed.append(label)

        # Stopped containers
        if clean_containers:
            self._runtime.set_log_file(self._registry.log_dir / "infra.log")
            for comp in self._registry.all_infra():
                st = self._runtime.status(comp)
                if st is ContainerStatus.STOPPED:
                    label = f"container: {comp.label} ({comp.name})"
                    if dry_run:
                        print(f"  (would remove) {label}")
                    else:
                        self._runtime.remove(comp)
                        print(f"  ✔ Removed {label}")
                    removed.append(label)

        # Venvs
        if clean_venvs:
            import shutil as _shutil
            for svc in self._registry.primary_services():
                if not self._venv.exists(svc, self._root):
                    continue
                svc_dir = self._root / svc.directory
                venv_dir = svc_dir / ("node_modules" if svc.type is ServiceType.NODE else "venv")
                label = f"venv: {svc.name} ({venv_dir})"
                if dry_run:
                    print(f"  (would remove) {label}")
                else:
                    _shutil.rmtree(venv_dir)
                    print(f"  ✔ Removed {label}")
                removed.append(label)

        if not removed:
            print("  Nothing to clean.")
        elif dry_run:
            print(f"\n  {len(removed)} item(s) would be removed. "
                  f"Run without --dry-run to proceed.")
        else:
            print(f"\n  ✔ Cleaned {len(removed)} item(s).")

    # -- private helpers -----------------------------------------------------

    def _detect_python(self) -> tuple[str, str]:
        """Returns (python_path, python_minor_str)."""
        py_min, py_max = self._registry.python_bounds()
        env_override = (os.environ.get("UNIFAI_PYTHON") or "").strip() or None
        python = python_detector.find_python(py_min, py_max, env_override=env_override)
        ver_out = subprocess.check_output(
            [python, "--version"], text=True,
        ).strip()
        version = ver_out.split()[-1]
        minor = ".".join(version.split(".")[:2])
        return python, minor

    @staticmethod
    def _validate_start(services: list[Service], *, fg: bool) -> None:
        non_primary = [s for s in services if not s.is_primary]
        primary = [s for s in services if s.is_primary]

        if not primary and non_primary:
            names = ", ".join(s.name for s in non_primary)
            raise SystemExit(
                f"❌ Cannot start only non-primary services ({names}).\n"
                f"   Non-primary services (workers) must be launched alongside "
                f"their parent service.\n"
                f"   Try a group like 'rag-stack' or 'agents' instead."
            )

        if fg:
            if len(services) != 1:
                raise SystemExit(
                    f"❌ Foreground mode (--fg) requires exactly one service, "
                    f"got {len(services)}."
                )
            if not services[0].is_primary:
                raise SystemExit(
                    f"❌ Cannot run non-primary service '{services[0].name}' "
                    f"in foreground mode."
                )

    def _build_context_command(self, svc: Service, python_minor: str) -> str:
        """Build the cd + venv-activate + env-source prefix for a service."""
        parts: list[str] = []
        svc_dir = self._root / svc.directory
        parts.append(f"cd {svc_dir}")

        if svc.type is ServiceType.PYTHON:
            parts.append("source venv/bin/activate")

        if svc.env_file:
            env_path = svc_dir / svc.env_file
            parts.append(f"set -a && source {env_path} 2>/dev/null; set +a")

        return " && ".join(parts)

    def _build_commands(
        self, services: list[Service], python_minor: str,
    ) -> dict[str, str]:
        """Build the full shell command for each service."""
        commands: dict[str, str] = {}
        for svc in services:
            context = self._build_context_command(svc, python_minor)
            launch = svc.launch
            if svc.type is ServiceType.PYTHON:
                launch = launch.replace("python ", f"python{python_minor} ")
            commands[svc.name] = f"{context} && {launch}"
        return commands

    @staticmethod
    def _build_default_layout(services: list[Service]) -> list[WindowLayout]:
        """Primary services in a 'services' window, workers in a 'workers' window."""
        primary = [s for s in services if s.is_primary]
        workers = [s for s in services if not s.is_primary]
        layout: list[WindowLayout] = []
        if primary:
            layout.append(WindowLayout(name="services", services=primary))
        if workers:
            layout.append(WindowLayout(name="workers", services=workers))
        return layout

    def _build_custom_layout(
        self,
        window_specs: list[tuple[str | None, list[str]]],
        bare_targets: list[str],
        all_services: list[Service],
    ) -> list[WindowLayout]:
        """Build layout from explicit --window specs and bare positional targets.

        *bare_targets* are positional args not inside any --window; they go
        into a default "services" window.  Services in *all_services* that
        don't appear in any window or bare target go into an "other" window.
        """
        by_name = {s.name: s for s in all_services}
        assigned: set[str] = set()
        layout: list[WindowLayout] = []

        if bare_targets:
            bare_svcs = self._registry.resolve_services(bare_targets)
            layout.append(WindowLayout(name="services", services=bare_svcs))
            assigned.update(s.name for s in bare_svcs)

        for i, (win_name, names) in enumerate(window_specs):
            svcs = [
                by_name[s.name]
                for s in self._registry.resolve_services(names)
                if s.name in by_name and s.name not in assigned
            ]
            if not svcs:
                continue
            if win_name is None:
                win_name = svcs[0].name if len(svcs) == 1 else f"window-{i}"
            layout.append(WindowLayout(name=win_name, services=svcs))
            assigned.update(s.name for s in svcs)

        remaining = [s for s in all_services if s.name not in assigned]
        if remaining:
            layout.append(WindowLayout(name="other", services=remaining))

        return layout

    def _kill_port(self, port: int) -> None:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True,
        )
        pids = result.stdout.strip()
        if pids:
            print(f"  ⚠ Killing process on port {port} (PIDs: {pids})")
            for pid in pids.splitlines():
                subprocess.run(
                    ["kill", "-9", pid.strip()],
                    capture_output=True,
                )

    @staticmethod
    def _is_port_in_use(port: int) -> bool:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True,
        )
        return bool(result.stdout.strip())

    def _print_summary(
        self, services: list[Service], infra: list,
    ) -> None:
        print()
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║              UnifAI Development Environment                 ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print(f"║  Session: {SESSION_NAME:<49}║")
        print("║                                                             ║")
        if infra:
            print("║  Infrastructure:                                            ║")
            for comp in infra:
                port_str = ", ".join(
                    p.split(":")[0] for p in comp.ports
                )
                line = f"    {comp.label:<20} (port {port_str})"
                print(f"║  {line:<57}║")
            print("║                                                             ║")
        primary = [s for s in services if s.is_primary]
        workers = [s for s in services if not s.is_primary]
        if primary:
            print("║  Services:                                                  ║")
            for svc in primary:
                port_info = f"port {svc.port}" if svc.port else ""
                line = f"    {svc.name:<20} ({port_info})"
                print(f"║  {line:<57}║")
        if workers:
            print("║  Workers:                                                   ║")
            for svc in workers:
                print(f"║    {svc.name:<55}║")
        print("║                                                             ║")
        print(f"║  Attach:  tmux attach -t {SESSION_NAME:<34}║")
        print(f"║  Destroy: unifai-dev destroy{' ':<31}║")
        print("║                                                             ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print()

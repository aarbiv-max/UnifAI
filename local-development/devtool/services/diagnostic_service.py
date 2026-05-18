"""Application service: health status and diagnostics."""

from __future__ import annotations

import subprocess
from pathlib import Path

from devtool.domain.registry import Registry
from devtool.ports.container_runtime import ContainerRuntime
from devtool.ports.health_checker import HealthChecker
from devtool.ports.process_manager import ProcessManager
from devtool.ports.session_manager import SessionManager
from devtool.services import env
from devtool.services.infra_service import InfraService
from devtool.services.venv_service import VenvService


class DiagnosticService:

    def __init__(
        self,
        registry: Registry,
        root: Path,
        runtime: ContainerRuntime,
        session: SessionManager,
        process_manager: ProcessManager,
        health_checker: HealthChecker,
        infra_service: InfraService,
        venv_service: VenvService,
    ) -> None:
        self._registry = registry
        self._root = root
        self._runtime = runtime
        self._session = session
        self._process = process_manager
        self._health = health_checker
        self._infra_svc = infra_service
        self._venv_svc = venv_service

    def status(self) -> None:
        infra, services, issues = self._health.build_dashboard(
            self._registry, self._runtime, self._session,
        )
        self._health.render_dashboard(infra, services, issues)

    def doctor(self) -> None:
        print("🩺 Running diagnostics…\n")

        try:
            python, python_minor = self._venv_svc.detect_python()
            print(f"  ✔ Python: {python} ({python_minor})")
        except RuntimeError as exc:
            print(f"  ✖ Python: {exc}")

        print(f"  ✔ Container runtime: {self._runtime.runtime_name}")

        print()
        self._infra_svc.status()

        print("\nVirtual environments:")
        venv_errors = self._venv_svc.check()

        print("\nEnvironment files:")
        for svc in self._registry.all_services():
            if svc.env_file:
                env_path = self._root / svc.directory / svc.env_file
                rel = env_path.relative_to(self._root)
                if env_path.exists():
                    print(f"  ✔ {svc.name}: {rel}")
                    missing = env.check_missing_keys(
                        svc, self._root, local_auth=self._registry.local_auth,
                    )
                    for key in sorted(missing):
                        print(f"  ⚠ {svc.name}: {rel}  {key} is missing (run 'unifai-dev start' or 'unifai-dev env generate')")
                    placeholders, auto_gen = env.check_unresolved(svc, self._root)
                    for key in placeholders:
                        print(f"  ⚠ {svc.name}: {rel}  {key} is still a placeholder!")
                    for key in auto_gen:
                        print(f"  ⚠ {svc.name}: {rel}  {key} is unresolved (run 'unifai-dev init' or 'unifai-dev env generate --force')")
                else:
                    if svc.env_entries:
                        print(f"  ✖ {svc.name}: {rel} missing")
                        print(f"    💡 Tip: run 'unifai-dev env generate' to generate the .env file.")
                    else:
                        print(f"  ✔ {svc.name}: {rel} shouldn't exist")

        print("\nPort availability:")
        for svc in self._registry.all_services():
            if svc.port:
                in_use = self._process.is_port_in_use(svc.port)
                icon = "⚠ in use" if in_use else "✔ free"
                print(f"  {icon}: port {svc.port} ({svc.name})")

    def logs(self, service_name: str, *, follow: bool = False) -> None:
        log_path = self._registry.log_dir / f"{service_name}.log"
        if not log_path.exists():
            print(f"No log file found at {log_path}")
            return

        cmd = ["tail", "-f", str(log_path)] if follow else ["cat", str(log_path)]
        subprocess.run(cmd)

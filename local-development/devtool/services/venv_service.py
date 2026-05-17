"""Application service: virtual environment management."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from devtool.domain.models import ServiceType
from devtool.domain.registry import Registry
from devtool.ports.python_resolver import PythonResolver
from devtool.ports.venv_manager import VenvManager


class VenvService:

    def __init__(
        self,
        registry: Registry,
        root: Path,
        venv_manager: VenvManager,
        python_resolver: PythonResolver,
    ) -> None:
        self._registry = registry
        self._root = root
        self._venv = venv_manager
        self._python_resolver = python_resolver

    def detect_python(self) -> tuple[str, str]:
        """Returns (python_path, python_minor_str)."""
        py_min, py_max = self._registry.python_bounds()
        env_override = (os.environ.get("UNIFAI_PYTHON") or "").strip() or None
        python = self._python_resolver.find_python(
            py_min, py_max, env_override=env_override,
        )
        ver_out = subprocess.check_output(
            [python, "--version"], text=True,
        ).strip()
        version = ver_out.split()[-1]
        minor = ".".join(version.split(".")[:2])
        return python, minor

    def setup(self, service_name: str | None = None, *, force: bool = False) -> None:
        python, _ = self.detect_python()
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

    def sync(self, service_name: str | None = None) -> None:
        """Update dependencies in existing venvs without recreating them."""
        python, _ = self.detect_python()
        if service_name:
            svc = self._registry.get_service(service_name)
            targets = [svc]
        else:
            targets = self._registry.primary_services()

        log_dir = self._registry.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        errors: list[str] = []

        print(f"🔄 Syncing virtual environments with {python}\n")
        for svc in targets:
            try:
                self._venv.sync(svc, python, self._root, log_dir=log_dir)
                print(f"  ✔ {svc.name}")
            except RuntimeError as exc:
                print(f"  ✖ {svc.name}: {exc}")
                errors.append(svc.name)

        if errors:
            print(f"\n⚠ Sync failed for: {', '.join(errors)}")
            print(f"  Check logs in {log_dir}/")
        else:
            print("\n✅ Dependencies synced.")

    def check(self) -> None:
        _, python_minor = self.detect_python()
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

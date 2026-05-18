"""Application service: .env file orchestration."""

from __future__ import annotations

from pathlib import Path

from devtool.domain.registry import Registry
from devtool.services import dotenv as env


class EnvService:

    def __init__(self, registry: Registry, root: Path) -> None:
        self._registry = registry
        self._root = root

    def generate(self, *, force: bool = False) -> None:
        print("🔧 Generating .env files…")
        generated, skipped, updated, warnings = env.generate_all(
            self._registry, self._root, force=force,
        )
        if generated:
            print(f"\nGenerated: {', '.join(generated)}")
        if updated:
            print(f"\nUpdated (added missing keys): {', '.join(updated)}")
        if skipped:
            print(
                f"\nPreserved existing (use --force to regenerate): "
                f"{', '.join(skipped)}"
            )
        for w in warnings:
            print(w)

    def show(self, service_name: str) -> None:
        svc = self._registry.get_service(service_name)
        env.show(svc, self._root)

    def auto_resolve_generated_keys(self) -> None:
        """Silently resolve any ``<AUTO_GENERATE>`` markers left in .env files."""
        grouped = env.collect_auto_generate_keys(
            self._registry, self._root,
        )
        if not grouped:
            return

        by_name = {s.name: s for s in self._registry.all_services()}
        value = env.get_or_create_shared_secret(self._root)

        for key, svc_names in grouped.items():
            services = [by_name[n] for n in svc_names if n in by_name]
            count = env.resolve_auto_generate_key(
                key, value, services, self._root,
            )
            print(f"  🔑 Auto-generated {key} for {count} service(s)")

    def resolve_auto_generate_keys(self, *, non_interactive: bool = False) -> None:
        """Prompt (or auto-resolve) ``<AUTO_GENERATE>`` env entries."""
        grouped = env.collect_auto_generate_keys(
            self._registry, self._root,
        )
        if not grouped:
            return

        by_name = {s.name: s for s in self._registry.all_services()}

        for key, svc_names in grouped.items():
            affected = ", ".join(svc_names)
            services = [by_name[n] for n in svc_names if n in by_name]

            if non_interactive:
                value = env.get_or_create_shared_secret(self._root)
                count = env.resolve_auto_generate_key(
                    key, value, services, self._root,
                )
                print(f"  ✔ {key}: auto-generated and applied to {count} service(s)")
                continue

            print(f"\n  🔑 {key} (used by: {affected}):")
            print(f"    [1] Auto-generate a shared dev key (recommended)")
            print(f"    [2] Enter your own value")
            choice = input("  Choice [1]: ").strip() or "1"

            if choice == "2":
                value = input(f"  Enter value for {key}: ").strip()
                if not value:
                    print(f"    ⏭ {key} skipped")
                    continue
            else:
                value = env.get_or_create_shared_secret(self._root)

            count = env.resolve_auto_generate_key(
                key, value, services, self._root,
            )
            print(f"    ✔ {key} applied to {count} service(s)")

    def resolve_placeholders(self, *, non_interactive: bool = False) -> None:
        """Prompt for ``<REPLACE...>`` placeholder values."""
        any_placeholders = False
        for svc in self._registry.all_services():
            placeholders, _ = env.check_unresolved(svc, self._root)
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
                        env.replace_env_value(env_path, key, value)
                        print(f"    ✔ {key} updated")
                    else:
                        print(f"    ⏭ {key} skipped")
        if not any_placeholders:
            print("  ✔ No placeholders to fill.")

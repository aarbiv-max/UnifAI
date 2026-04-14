"""SSO Backend service definition for local development."""

from __future__ import annotations

from pathlib import Path

from core.base_service import BaseService, PatchSpec


class SsoService(BaseService):

    @property
    def name(self) -> str:
        return "sso"

    @property
    def directory(self) -> Path:
        return Path("shared-resources/sso-backend")

    @property
    def port(self) -> int | None:
        return int(self._config.sso_port)

    def env_entries(self) -> dict[str, str] | None:
        return {
            "keycloak_base_url": self._config.keycloak_base_url,
            "client_id": "<REPLACE_WITH_YOUR_CLIENT_ID>",
            "client_secret": "<REPLACE_WITH_YOUR_CLIENT_SECRET>",
            "keycloak_realm": self._config.keycloak_realm,
            "hostname_local": self._config.sso_host,
            "port": self._config.sso_port,
            "frontend_url": self._config.frontend_url,
            "backend_env": "development",
        }

    @property
    def env_file_path(self) -> Path | None:
        return self._root / "shared-resources" / "sso-backend" / ".env"

    def patch_specs(self) -> list[PatchSpec]:
        return [
            PatchSpec(
                file=Path("shared-resources/sso-backend/app.py"),
                find="app.run(host=config.hostname_local, port=config.port, debug=True)",
                replace='app.run("0.0.0.0", port=config.port, debug=True)',
            ),
        ]

    def post_apply_message(self) -> str | None:
        env_path = self.env_file_path
        if env_path and env_path.exists() and "<REPLACE_WITH_YOUR_CLIENT_ID>" in env_path.read_text():
            return (
                "⚠️  Action required: edit shared-resources/sso-backend/.env and replace"
                "\n   the client_id and client_secret placeholders with your actual credentials."
            )
        return None

    def run_command(self) -> str:
        d = self.absolute_directory
        return (
            f"cd {d} && source venv/bin/activate"
            f" && set -a && source .env 2>/dev/null; set +a"
            f" && python app.py"
        )

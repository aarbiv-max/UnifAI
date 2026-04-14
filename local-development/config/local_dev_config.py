"""Local development configuration — zero external dependencies."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields


@dataclass
class LocalDevConfig:
    """
    Centralizes all local-development environment settings.

    Every field can be overridden via an environment variable of the same name
    (case-insensitive).  For example ``export RAG_PORT=9999`` overrides
    ``rag_port``.
    """

    rag_port: str = "13457"
    rag_host: str = "127.0.0.1"

    ui_port: str = "5000"
    ui_host: str = "0.0.0.0"

    sso_port: str = "13456"
    sso_host: str = "127.0.0.1"

    multi_agent_port: str = "8002"
    multi_agent_host: str = "0.0.0.0"

    backend_port: str = "8005"
    backend_host: str = "0.0.0.0"

    frontend_url: str = "http://127.0.0.1:5000"

    keycloak_base_url: str = "https://auth.stage.redhat.com/auth"
    keycloak_realm: str = "EmployeeIDP"

    python_min: str = "3.11"
    python_max: str = "3.13"

    def __post_init__(self) -> None:
        for f in fields(self):
            env_val = os.environ.get(f.name.upper(), "").strip()
            if env_val:
                object.__setattr__(self, f.name, env_val)

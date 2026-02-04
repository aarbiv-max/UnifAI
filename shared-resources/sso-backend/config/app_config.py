"""SSO backend application configuration defaults."""

from global_utils.config.config import SharedConfig


class AppConfig(SharedConfig):
    """Runtime configuration values for the SSO backend service."""

    hostname_local: str = "127.0.0.1"
    port: str = "13456"

    # Keycloak Configuration (for internal SSO users)
    keycloak_base_url: str = "https://auth.stage.redhat.com/auth"
    client_id: str = "TAG-001"
    client_secret: str = "a0a82b17-e7e7-49c6-ad1c-3d03c79ff4fd"
    keycloak_realm: str = "EmployeeIDP"
    version: str = "1.0.0"

    # MongoDB Configuration (inherited from SharedConfig but can be overridden)
    # mongodb_ip: str = "localhost"  # from SharedConfig
    # mongodb_port: str = "27017"    # from SharedConfig

    frontend_url: str = "http://127.0.0.1:5000/"    # session_cookie_secure=True
    backend_env: str = "development"


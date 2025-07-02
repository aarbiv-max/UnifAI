from global_utils.config.config import SharedConfig

class AppConfig(SharedConfig):
    rabbitmq_port: str = "5672"
    rabbitmq_ip: str = "0.0.0.0"
    broker_user_name: str = "guest"
    broker_password: str = "guest"

    mongodb_port: str = "27017"
    mongodb_ip: str = "0.0.0.0"

    hostname: str = "0.0.0.0"
    hostname_local: str = "127.0.0.1"
    port: str = "13456"

    qdrant_ip: str = "http://localhost"
    qdrant_port: str = "6333"

    # Keycloak Configuration
    keycloak_base_url: str = "https://auth.stage.redhat.com/auth"
    client_id: str = "TAG-001"
    client_secret: str = "a0a82b17-e7e7-49c6-ad1c-3d03c79ff4fd"
    keycloak_realm: str = "EmployeeIDP"

    # Flask Configuration
    # secret_key=your-super-secret-key-change-this-in-production
    frontend_url: str = "http://localhost:5000"
    # session_cookie_secure=True
    backend_env: str = "development"
    @classmethod
    def get(cls, key: str, default=None):
        instance = cls()  # safe because of SingletonMeta
        return getattr(instance, key, default)
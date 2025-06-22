from global_utils.config.config import SharedConfig

class AppConfig(SharedConfig):
    rabbitmq_port: str = "5672"
    rabbitmq_ip: str = "0.0.0.0"
    broker_user_name: str = "guest"
    broker_password: str = "guest"
    mongodb_port: str = "27017"
    mongodb_ip: str = "0.0.0.0"
    hostname: str = "0.0.0.0"
    port: str = "13456"
    qdrant_ip: str = "http://localhost"
    qdrant_port: str = "6333"
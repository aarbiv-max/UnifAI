from global_utils.config.config import SharedConfig


class AppConfig(SharedConfig):
    rabbitmq_port: str = "5672"
    rabbitmq_ip: str = "0.0.0.0"
    broker_user_name: str = "guest"
    broker_password: str = "guest"

    mongodb_port: str = "27017"
    mongodb_ip: str = "0.0.0.0"

    hostname_local: str = "0.0.0.0"
    port: str = "13456"

    qdrant_ip: str = "0.0.0.0"
    qdrant_port: str = "6333"
    
    docling_service_url: str = "http://docling-service:5001"
    docling_service_timeout: int = 300
    
    embedding_service_url: str = "http://embedding-service:5002"
    embedding_service_timeout: int = 60
    embedding_service_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Slack Configuration
    # When running locally, use the default slack tokens ( get it from genie-cred-data and use ENV to set it)
    default_slack_bot_token: str = ""
    default_slack_user_token: str = ""

    # Flask Configuration
    # secret_key=your-super-secret-key-change-this-in-production

    frontend_url: str = "http://localhost:5000"
    upload_folder: str = "/app/shared"
    # session_cookie_secure=True
    backend_env: str = "development"
    version: str = "1.0.0"

    # qdrant_ip: str = "http://a467739e076d04bf1b15aa68187cbc05-1112405490.us-east-1.elb.amazonaws.com"
    # mongodb_ip: str = "ae8f0dd8e6cd046539c3f0b7c6a75f13-508991814.us-east-1.elb.amazonaws.com"
    # rabbitmq_ip: str = "a509af714a5fa4810bf879cfc8823456-1634716882.us-east-1.elb.amazonaws.com"
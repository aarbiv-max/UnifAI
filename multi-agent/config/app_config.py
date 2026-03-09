from global_utils.config.config import SharedConfig


class AppConfig(SharedConfig):
    mongo_db: str = "UnifAI"
    blueprint_coll: str = "blueprints"
    resources_coll: str = "resources"
    session_coll: str = "workflow_sessions"
    shares_coll: str = "shares"
    templates_coll: str = "templates"
    hostname: str = "0.0.0.0"
    port: str = "8002"
    version: str = "1.0.0"
    admin_allowed_users: list = []  # Populate with user_ids (usernames) to grant admin access
    
    # Engine
    engine_name: str = "langgraph"

    # Redis Configuration (for session streaming)
    redis_ip: str = "0.0.0.0"
    redis_port: str = "6379"
    redis_db: int = 0
    redis_password: str = ""
    redis_stream_maxlen: int = 5000
    redis_stream_ttl_seconds: int = 3600

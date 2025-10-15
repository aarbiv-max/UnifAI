from global_utils.config.config import SharedConfig


class AppConfig(SharedConfig):
    mongo_db: str = "UnifAI"
    blueprint_coll: str = "blueprints"
    resources_coll: str = "resources"
    session_coll: str = "workflow_sessions"
    shares_coll: str = "shares"
    hostname: str = "0.0.0.0"
    port: str = "8002"
    version: str = "1.0.0"

    # Engine
    engine_name: str = "langgraph"

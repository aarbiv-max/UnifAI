from global_utils.config.config import SharedConfig


class AppConfig(SharedConfig):
    mongo_db: str = "UnifAI"
    blueprint_coll: str = "blueprints"
    resources_coll: str = "resources"
    session_coll: str = "workflow_sessions"
    shares_coll: str = "shares"
    templates_coll: str = "templates"
    hostname: str = "127.0.0.1"
    port: str = "8002"
    version: str = "1.0.0"
    admin_allowed_users: list = ["mcarmi"]  # Populate with user_ids (usernames) to grant admin access
    # Engine
    engine_name: str = "temporal"
    temporal_task_queue: str = "graph-engine"
    # Redis streaming tuning
    redis_stream_ttl: int = 3600
    redis_stream_block_ms: int = 5000
    redis_stream_batch_size: int = 50

    # Collaboration hub — Redis-backed multi-user session presence
    collaboration_presence_ttl: int = 300
    # Team workspace — transient edit locks (resources / blueprints), seconds
    collaboration_edit_lock_ttl_sec: int = 180

    # Directory provider: "sso" (via SSO pod) or "" to disable
    directory_provider: str = ""
    directory_timeout: int = 10

    # SSO directory URL (used when directory_provider="sso")
    directory_sso_url: str = ""

    # Shared secret for the workspace.cleanup internal endpoint.
    # Must match the value sent by the SSO backend in X-Internal-Secret.
    cleanup_secret: str = ""

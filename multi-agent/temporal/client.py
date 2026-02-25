from temporalio.client import Client
from config.app_config import AppConfig


async def get_temporal_client() -> Client:
    """Create a Temporal client connection from AppConfig settings."""
    cfg = AppConfig.get_instance()
    return await Client.connect(
        cfg.temporal_host,
        namespace=cfg.temporal_namespace,
    )

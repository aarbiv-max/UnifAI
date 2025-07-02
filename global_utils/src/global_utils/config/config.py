from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, Dict, Callable
from .sources import DotEnvSource, YamlSource, JsonSource
from ..utils.singleton import SingletonMeta

SettingsSource = Callable[[], Dict[str, Any]]
    
class SharedConfig(BaseSettings, metaclass=SingletonMeta):
    """
    Anything every app needs.
    """
    mongodb_port: str = "27017"
    mongodb_ip: str = "localhost"
    rabbitmq_port: str = "5672"
    rabbitmq_ip: str = "localhost"
    
    # shared loading order
    model_config = SettingsConfigDict(
        env_prefix="",
        settings_customise_sources=lambda init, env, fs: (
            init,
            env,
            DotEnvSource().load,
            YamlSource().load,
            JsonSource().load,
            fs,
        ),
    )

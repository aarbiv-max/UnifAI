"""Base configuration manager - infrastructure adapter."""
import os
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from shared.logger import logger


class BaseConfigurationManager(ABC):
    """
    Base configuration manager with file loading capability.
    
    Provides common configuration management functionality including:
    - JSON config file loading/saving
    - Secrets management
    - Key-value config storage
    
    Matches backend's ConfigurationManager behavior for consistency.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Create a BaseConfigurationManager and initialize internal storage for configuration and secrets.
        
        If `config_path` is provided and the file exists, load configuration and secrets from that JSON file.
        
        Parameters:
            config_path (Optional[str]): Path to a JSON file containing top-level "config" and "secrets" objects. If omitted or the file does not exist, the manager starts with empty stores.
        """
        self._config: Dict[str, Any] = {}
        self._secrets: Dict[str, Any] = {}
        
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> None:
        """
        Load configuration and secrets from a JSON file into the manager's in-memory stores.
        
        The file should contain a top-level JSON object with optional "config" and "secrets" mappings. Keys from "config" are merged into self._config and keys from "secrets" are merged into self._secrets; missing sections are treated as empty mappings. Any exception raised while opening, reading, or parsing the file is propagated.
        
        Parameters:
            config_path (str): Path to the JSON configuration file containing "config" and "secrets".
        """
        logger.info(f"Loading configuration from {config_path}")
        try:
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                self._config.update(loaded_config.get('config', {}))
                self._secrets.update(loaded_config.get('secrets', {}))
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {str(e)}")
            raise
    
    def save_config(self, config_path: str) -> None:
        """
        Persist the manager's configuration and secrets to the given JSON file.
        
        Writes a JSON object with top-level keys "config" (the configuration dict) and "secrets" (the secrets dict).
        """
        try:
            with open(config_path, 'w') as f:
                json.dump({
                    'config': self._config,
                    'secrets': self._secrets
                }, f, indent=2)
            logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {config_path}: {str(e)}")
            raise
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from the manager's configuration by key.
        
        Parameters:
            key (str): Configuration key to look up.
            default (Any): Value to return if the key is not present.
        
        Returns:
            Any: The stored value for `key`, or `default` if the key is absent.
        """
        return self._config.get(key, default)
    
    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set or update an in-memory configuration entry.
        
        Parameters:
            key: The configuration key to set.
            value: The value to assign to the configuration key.
        """
        self._config[key] = value
    
    def get_secret(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a secret value by key.
        
        Parameters:
            key (str): The secret's key.
            default (Any): Value to return if the key is not present.
        
        Returns:
            The secret value associated with `key`, or `default` if the key is absent.
        """
        return self._secrets.get(key, default)
    
    def set_secret(self, key: str, value: Any) -> None:
        """
        Set a secret value identified by `key`.
        
        Parameters:
            key (str): The secret's identifier.
            value (Any): The secret value to store.
        """
        self._secrets[key] = value
    
    @abstractmethod
    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate the current in-memory configuration and collect any validation errors.
        
        Performs checks defined by subclasses and reports whether the configuration is valid.
        
        Returns:
            tuple: (is_valid, errors) where `is_valid` is `True` if no validation errors were found, `False` otherwise; `errors` is a list of human-readable error messages describing validation failures.
        """
        pass


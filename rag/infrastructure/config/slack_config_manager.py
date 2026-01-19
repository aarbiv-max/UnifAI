"""Slack configuration manager - infrastructure adapter."""
from typing import Dict, List, Optional, Any, Tuple
from infrastructure.config.base_config_manager import BaseConfigurationManager


class SlackConfigManager(BaseConfigurationManager):
    """
    Configuration manager for Slack integration.
    
    Manages Slack-specific configuration and credentials, including OAuth tokens.
    Inherits file loading capability from BaseConfigurationManager.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Slack configuration manager and load any saved project tokens.
        
        Creates the internal mapping for per-project OAuth tokens and, if the configuration contains a 'project_tokens' section, populates that mapping from the configuration.
        
        Parameters:
            config_path (Optional[str]): Path to a configuration file to load (if None, uses default locations).
        """
        super().__init__(config_path)
        self._project_tokens: Dict[str, Dict[str, str]] = {}
        
        # Auto-load project tokens if available in the configuration (matches backend behavior)
        project_tokens = self.get_config_value('project_tokens', {})
        for project_id, tokens in project_tokens.items():
            self.set_project_tokens(project_id, tokens.get('user_token'), tokens.get('bot_token'))
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate that at least one project is configured and that every configured project has a bot token.
        
        Returns:
            Tuple[bool, List[str]]: `True` if the configuration has at least one project and every project includes a bot token, `False` otherwise; second element is a list of error messages describing any missing configuration.
        """
        errors = []
        
        # Check if we have at least one project configured
        if not self._project_tokens:
            errors.append("No project tokens configured")
        
        # Check each project's configuration
        for project_id, tokens in self._project_tokens.items():
            if not tokens.get('bot_token'):
                errors.append(f"Missing bot token for project {project_id}")
        
        return len(errors) == 0, errors
    
    def set_project_tokens(self, project_id: str, user_token: Optional[str] = None, 
                         bot_token: Optional[str] = None) -> None:
        """
                         Set or update OAuth tokens for a project and synchronize them into the manager's configuration.
                         
                         Parameters:
                         	project_id (str): The project identifier for which to store tokens.
                         	user_token (Optional[str]): User OAuth token to set for the project; if omitted, the existing user token is left unchanged.
                         	bot_token (Optional[str]): Bot OAuth token to set for the project; if omitted, the existing bot token is left unchanged.
                         """
        if project_id not in self._project_tokens:
            self._project_tokens[project_id] = {}
        
        if user_token:
            self._project_tokens[project_id]['user_token'] = user_token
        
        if bot_token:
            self._project_tokens[project_id]['bot_token'] = bot_token
        
        # Update the configuration dictionary
        self._config['project_tokens'] = self._project_tokens
    
    def get_project_tokens(self, project_id: str) -> Dict[str, str]:
        """
        Return the OAuth tokens configured for the given project.
        
        Parameters:
            project_id (str): Project identifier whose tokens to retrieve.
        
        Returns:
            Dict[str, str]: Mapping containing `'user_token'` and/or `'bot_token'` for the project.
        
        Raises:
            KeyError: If no tokens are configured for `project_id`.
        """
        if project_id not in self._project_tokens:
            raise KeyError(f"No tokens configured for project {project_id}")
        
        return self._project_tokens[project_id]
    
    def get_default_project(self) -> Optional[str]:
        """
        Get the default project ID.
        
        Returns:
            The default project ID or None if not set
        """
        return self.get_config_value('default_project')
    
    def set_default_project(self, project_id: str) -> None:
        """
        Set the default project used by the manager.
        
        Parameters:
            project_id (str): Project identifier to set as the default.
        
        Raises:
            KeyError: If `project_id` is not present in the configured project tokens.
        """
        if project_id not in self._project_tokens:
            raise KeyError(f"Cannot set default project to {project_id}; not in project tokens")
        
        self.set_config_value('default_project', project_id)
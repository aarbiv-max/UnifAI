"""Base data connector - domain port."""
from abc import ABC, abstractmethod
from typing import List, Any


class DataConnector(ABC):
    """
    Abstract base class for data collection components.
    
    Provides a common interface for retrieving data from various sources.
    """
    
    def __init__(self, config_manager: Any):
        """
        Initialize the DataConnector with a configuration manager and default internal state.
        
        Parameters:
            config_manager (Any): Provides configuration, credentials, or services required by the connector.
        """
        self._config_manager = config_manager
        self._base_url: str = ""
        self._available_apis: List[str] = []
    
    @property
    def base_url(self) -> str:
        """
        Base URL used for API calls.
        
        Returns:
            The base URL string for constructing API endpoints.
        """
        return self._base_url
    
    @base_url.setter
    def base_url(self, url: str) -> None:
        """
        Set the base URL used for API calls.
        
        Parameters:
            url (str): The base URL to use for subsequent API requests.
        """
        self._base_url = url
    
    @property
    def available_apis(self) -> List[str]:
        """
        Retrieve the configured available API endpoint identifiers.
        
        Returns:
            List[str]: The list of available API endpoint identifiers.
        """
        return self._available_apis
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the data source.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Verify that a working connection to the data source can be established.
        
        Returns:
            True if the connection is successful, False otherwise.
        """
        pass

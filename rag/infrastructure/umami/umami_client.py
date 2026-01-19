"""Umami Analytics client - external API adapter."""
from typing import Dict, Any

import umami

from shared.logger import logger


class UmamiClient:
    """
    Infrastructure adapter for Umami Analytics API.
    
    Handles authentication and website information retrieval
    from the Umami analytics service.
    """

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
    ):
        """
        Create a configured UmamiClient and authenticate with the Umami service using the provided credentials.
        
        Parameters:
            url (str): Base URL of the Umami service.
            username (str): Username used to authenticate with Umami.
            password (str): Password used to authenticate with Umami.
        
        Raises:
            ValueError: If any configuration value is missing or invalid.
        """
        self._url = url
        self._username = username
        self._password = password
        self._website_cache: Dict[str, Dict[str, Any]] = {}
        
        self._validate_config()
        self._login()

    def _validate_config(self) -> None:
        """
        Validate Umami configuration and raise a ValueError for missing or placeholder credentials.
        
        Raises:
            ValueError: If the URL is empty or "0.0.0.0"; if the username is empty or "dummy"; or if the password is empty or "dummy".
        """
        if not self._url or self._url == "0.0.0.0":
            raise ValueError("Umami URL is not configured")
        if not self._username or self._username == "dummy":
            raise ValueError("Umami username is not configured")
        if not self._password or self._password == "dummy":
            raise ValueError("Umami password is not configured")

    def _login(self) -> None:
        """
        Set the Umami base URL and authenticate using the configured credentials so the client can perform API requests.
        """
        umami.set_url_base(self._url)
        umami.login(self._username, self._password)
        logger.info("Umami client authenticated successfully")

    def get_website_id(self, website_name: str) -> Dict[str, Any]:
        """
        Retrieve the Umami website ID for a given website name and cache the result.
        
        Looks up the website by name via the Umami API, stores the mapping in an internal cache to avoid repeated requests, and returns the Umami base URL alongside the site's ID.
        
        Parameters:
            website_name (str): Name of the website in Umami to look up.
        
        Returns:
            dict: Dictionary with keys:
                - "umami_url" (str): The configured Umami base URL.
                - "website_id": The ID of the matched website.
        
        Raises:
            ValueError: If no website with the given name is found in Umami.
        """
        # Check cache first
        if website_name in self._website_cache:
            return self._website_cache[website_name]

        try:
            websites = umami.websites()
            website_info = next(w for w in websites if w.name == website_name)
            
            result = {
                "umami_url": self._url,
                "website_id": website_info.id,
            }
            
            # Cache the result
            self._website_cache[website_name] = result
            logger.info(f"Retrieved Umami website ID for: {website_name}")
            
            return result
            
        except StopIteration:
            logger.error(f"Umami website not found: {website_name}")
            raise ValueError(f"Website '{website_name}' not found in Umami")
        except Exception as e:
            logger.error(f"Failed to get Umami website ID for {website_name}: {e}")
            raise

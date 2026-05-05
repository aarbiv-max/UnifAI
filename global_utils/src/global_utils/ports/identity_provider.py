from abc import ABC, abstractmethod
from typing import Dict, Any

class IdentityProvider(ABC):
    @abstractmethod
    def validate_session(self, token: str) -> Dict[str, Any]:
        """Validate a session token against the identity provider."""
        pass

    @abstractmethod
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Fetch user profile details from the identity provider."""
        pass
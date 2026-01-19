"""TermsApproval domain model."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class TermsApproval:
    """Domain model for user terms approval."""
    username: str
    approved_at: datetime
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TermsApproval":
        """
        Construct a TermsApproval instance from a dictionary.
        
        Parameters:
            data (Dict[str, Any]): Dictionary that may contain the keys
                'username', 'approved_at', and 'created_at'. Missing 'username'
                defaults to an empty string; missing 'approved_at' defaults to the
                current UTC time.
        
        Returns:
            TermsApproval: A TermsApproval populated from the provided dictionary.
        """
        return cls(
            username=data.get("username", ""),
            approved_at=data.get("approved_at", datetime.utcnow()),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a dictionary mapping the instance's field names to their values.
        
        Returns:
            dict: A dictionary with keys 'username', 'approved_at', and 'created_at' mapped to their corresponding values from this TermsApproval instance.
        """
        return asdict(self)
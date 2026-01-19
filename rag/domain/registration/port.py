"""Registration port - abstract interface for registration use cases."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

from domain.registration.model import BaseSourceData


class RegistrationPort(ABC):
    """
    Abstract base for source registration flows.

    Implementations should orchestrate validation and persistence while preserving
    the existing behavior for their specific source type.
    
    Supports skip_validation flag:
    - When False (default): Full validation is performed (for external API calls)
    - When True: Skip pre-upload validations, only perform content-based validation
      like MD5 duplicate checking (for UI calls that pre-validated via /docs/validate)
    """

    # Subclasses must define this
    DATA_SOURCE_TYPE: str = ""

    @property
    @abstractmethod
    def source_data(self) -> BaseSourceData:
        """
        Expose the aggregated, immutable source data for this registration instance.
        
        Returns:
            BaseSourceData: Aggregated, immutable source data containing fields such as `id`, `name`, `pipeline_id`, and `form_data`.
        """
        ...

    @abstractmethod
    def run_validator(self) -> Tuple[bool, Dict[str, Any] | None]:
        """
        Validate the current source data for a single registration instance.
        
        Returns:
            tuple: A pair (is_valid, issue) where:
                is_valid (bool): `True` if validation succeeded, `False` otherwise.
                issue (dict | None): Structured validation issues when `is_valid` is `False`, otherwise `None`.
        """
        ...

    @abstractmethod
    def register(self) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
        """
        Persist the source represented by this port and return the persisted data or structured issues.
        
        Concrete implementations perform the actual registration/persistence and report any structured issues encountered.
        
        Returns:
            registered_source_dict (Dict[str, Any] | None): Data for the registered source when registration succeeds, otherwise None.
            issue_dict (Dict[str, Any] | None): Structured information describing validation or registration problems when registration fails, otherwise None.
        """
        ...

    def run_registration(self) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
        """
        Orchestrates validation and registration for a single source instance.
        
        Performs validation via run_validator and, only if valid, performs registration via register().
        Returns:
            (registered_source_dict, issue_dict): `registered_source_dict` is the registered source data when registration succeeds, otherwise `None`. `issue_dict` contains validation or registration issues when present, otherwise `None`.
        """
        is_valid, issue = self.run_validator()
        if not is_valid:
            return None, issue
        return self.register()
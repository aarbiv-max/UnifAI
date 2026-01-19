"""Registration service - orchestrates registration flows."""
from __future__ import annotations

from typing import Any, Dict, List

from application.registration.factory import RegistrationFactory
from shared.logger import logger


class RegistrationService:
    """
    Synchronous registration service that creates registration flow instances
    and executes them.
    
    The service supports a skip_validation flag for pre-validated files:
    - When skip_validation=False (default): Full validation is performed
    - When skip_validation=True: Only MD5 duplicate check is performed
    
    Note: MD5 duplicate checking always runs regardless of skip_validation
    because it requires the actual file content and can only be checked
    after the file is uploaded.
    """

    def __init__(self, factory: RegistrationFactory) -> None:
        """
        Initialize the service with a factory for creating registrar instances.
        
        Parameters:
            factory (RegistrationFactory): Factory used to create per-source registrar instances invoked during registration flows.
        """
        self._factory = factory

    def register_sources(
        self,
        *,
        data_list: List[Dict[str, Any]],
        source_type: str,
        upload_by: str,
        skip_validation: bool = False,
    ) -> Dict[str, Any]:
        """
        Register the given source data items and return the aggregated results.
        
        Parameters:
            data_list (List[Dict[str, Any]]): Source data dictionaries to register.
            source_type (str): Type of the source (e.g., 'DOCUMENT', 'SLACK').
            upload_by (str): Username of the uploader.
            skip_validation (bool): If True, skip pre-upload validations (extension, size, name).
                The MD5 duplicate check is always performed; set True only for pre-validated UI uploads.
        
        Returns:
            Dict[str, Any]: A dictionary with:
                - status (str): "registration_complete".
                - registered_sources (List[Dict[str, Any]]): Successfully registered source records.
                - issues (List[Dict[str, Any]]): Issues encountered during registration.
        """
        logger.info(
            f"Starting synchronous registration for {len(data_list)} {source_type} sources "
            f"by user {upload_by} (skip_validation={skip_validation})"
        )

        registered_sources: List[Dict[str, Any]] = []
        issues: List[Dict[str, Any]] = []

        for instance in data_list:
            registrar = self._factory.create(
                source_type=source_type,
                upload_by=upload_by,
                instance=instance,
                skip_validation=skip_validation,
            )
            registered, issue = registrar.run_registration()
            if issue is not None:
                issues.append(issue)
                continue
            if registered is not None:
                registered_sources.append(registered)

        return {
            "status": "registration_complete",
            "registered_sources": registered_sources,
            "issues": issues,
        }
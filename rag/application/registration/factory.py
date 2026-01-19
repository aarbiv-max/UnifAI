"""Registration factory - creates registration instances."""
from __future__ import annotations

from typing import Any, Dict

from domain.registration.port import RegistrationPort
from domain.data_source.repository import DataSourceRepository
from application.registration.document_registration import DocumentRegistration
from application.registration.slack_registration import SlackRegistration
from application.validation.validators.document import DocValidators
from application.validation.validators.slack import SlackValidators


class RegistrationFactory:
    """
    Factory to create registration flows based on data source type.
    
    Supports skip_validation flag for pre-validated files:
    - When skip_validation=False (default): Full validation during registration
    - When skip_validation=True: Only MD5 duplicate check (files pre-validated via /docs/validate)
    """

    def __init__(
        self,
        data_source_repository: DataSourceRepository,
        upload_folder: str,
        doc_validators: DocValidators,
        slack_validators: SlackValidators,
    ) -> None:
        """
        Initialize the factory with dependencies required to create registration flows.
        
        Parameters:
            data_source_repository (DataSourceRepository): Repository used to persist or look up data source records.
            upload_folder (str): Filesystem path where uploaded documents are stored.
            doc_validators (DocValidators): Validators applied to document uploads.
            slack_validators (SlackValidators): Validators applied to Slack uploads.
        """
        self._data_source_repository = data_source_repository
        self._upload_folder = upload_folder
        self._doc_validators = doc_validators
        self._slack_validators = slack_validators

    def create(
        self,
        source_type: str,
        upload_by: str,
        instance: Dict[str, Any],
        skip_validation: bool = False,
    ) -> RegistrationPort:
        """
        Create a configured registration flow instance for the specified data source type.
        
        If `skip_validation` is True, pre-upload validations (extension, size, name) are skipped; an MD5 duplicate check is always performed.
        
        Parameters:
            source_type (str): Data source type (case-insensitive), e.g. "slack" or "document".
            upload_by (str): Identifier of the user initiating the upload.
            instance (Dict[str, Any]): Payload describing the data source instance to register.
            skip_validation (bool): When True, skip pre-upload validators; defaults to False.
        
        Returns:
            RegistrationPort: A registration instance configured for the requested source type.
        
        """
        normalized = (source_type or "").strip().lower()

        if normalized == "slack":
            return SlackRegistration(
                data_source_repository=self._data_source_repository,
                upload_by=upload_by,
                instance=instance,
                slack_validators=self._slack_validators,
                skip_validation=skip_validation,
            )

        if normalized == "document":
            return DocumentRegistration(
                data_source_repository=self._data_source_repository,
                upload_by=upload_by,
                instance=instance,
                upload_folder=self._upload_folder,
                doc_validators=self._doc_validators,
                skip_validation=skip_validation,
            )

        raise ValueError(f"Unsupported source type: {source_type}")
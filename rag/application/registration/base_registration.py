"""Base registration implementation with common persistence logic."""
from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, Tuple
from datetime import datetime

from domain.registration.port import RegistrationPort
from domain.registration.model import BaseSourceData
from domain.data_source.model import DataSource
from domain.data_source.repository import DataSourceRepository
from shared.logger import logger


class BaseRegistration(RegistrationPort):
    """
    Base implementation for source registration flows.
    
    Provides common persistence and logging logic while delegating
    source-specific behavior to subclasses.
    
    Supports skip_validation flag:
    - When False (default): Full validation is performed (for external API calls)
    - When True: Skip pre-upload validations, only perform content-based validation
      like MD5 duplicate checking (for UI calls that pre-validated via /docs/validate)
    """

    def __init__(
        self,
        data_source_repository: DataSourceRepository,
        upload_by: str,
        instance: Dict[str, Any],
        skip_validation: bool = False,
    ) -> None:
        """
        Initialize the registration with its repository, uploader identity, instance context, and validation flag.
        
        Parameters:
            data_source_repository (DataSourceRepository): Repository used to persist DataSource entities.
            upload_by (str): Identifier of the user or system performing the registration.
            instance (Dict[str, Any]): Instance-level context (for example, configuration or tags) used during registration.
            skip_validation (bool): If `True`, skip validation steps during registration; if `False`, perform validation.
        """
        self._data_source_repository = data_source_repository
        self.upload_by = upload_by
        self.instance = instance
        self.skip_validation = skip_validation

    def register(self) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
        """
        Register the instance, persist the resulting source, and produce a registered-source representation.
        
        Persists source data constructed from subclass-provided metadata and type data, logs the registration, and returns the response payload and any processing issues.
        
        Returns:
            registered_source (Dict[str, Any] | None): Dictionary describing the registered source (pipeline_id, metadata, source_type, upload_by, type_data) or None if registration did not produce a representation.
            issue_dict (Dict[str, Any] | None): Dictionary of validation or processing issues; `None` when there are no issues.
        """
        metadata = self._build_metadata()
        type_data = self._build_type_data()

        # Persist via repository
        self._persist(type_data)

        # Build response
        registered_source = self._build_registered_source(metadata, type_data)

        # Log
        self._log_registered()

        return registered_source, None

    def _persist(self, type_data: Dict[str, Any]) -> None:
        """
        Persist the constructed DataSource entity to the configured data source repository.
        
        Parameters:
        	type_data (Dict[str, Any]): Source-specific type payload to store on the DataSource record.
        """
        now = datetime.utcnow()
        source = DataSource(
            source_id=self.source_data.source_id,
            source_name=self.source_data.source_name,
            source_type=self.DATA_SOURCE_TYPE,
            pipeline_id=self.source_data.pipeline_id,
            upload_by=self.upload_by,
            created_at=now,
            last_sync_at=now,
            tags=self.instance.get("tags", []),
            type_data=type_data,
        )
        self._data_source_repository.save(source)

    def _build_registered_source(
        self,
        metadata: Any,
        type_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Constructs the response dictionary representing a registered data source.
        
        Parameters:
        	metadata (Any): Source-specific metadata object or mapping. If an object with attributes, it will be serialized to a dict.
        	type_data (Dict[str, Any]): Source-specific type data.
        
        Returns:
        	registered_source (Dict[str, Any]): Dictionary containing `pipeline_id`, `metadata`, `source_type`, `upload_by`, and `type_data`.
        """
        return {
            "pipeline_id": self.source_data.pipeline_id,
            "metadata": metadata.__dict__ if hasattr(metadata, "__dict__") else metadata,
            "source_type": self.DATA_SOURCE_TYPE,
            "upload_by": self.upload_by,
            "type_data": type_data,
        }

    def _log_registered(self) -> None:
        """
        Emit an info-level log recording the registered data source's type, name, pipeline_id, and optional form data.
        """
        metadata_info = f" with form data: {self.source_data.form_data}" if self.source_data.form_data else ""
        logger.info(
            f"Registered {self.DATA_SOURCE_TYPE} source: {self.source_data.source_name} "
            f"with pipeline_id: {self.source_data.pipeline_id}{metadata_info}"
        )

    @abstractmethod
    def _build_metadata(self) -> Any:
        """
        Construct the source-specific metadata needed for registration.
        
        Subclasses must provide a metadata object or dictionary that represents the source. If a plain object is returned, its attributes should be suitable for serialization via `__dict__` (or otherwise JSON-serializable).
        
        Returns:
            metadata (Any): A metadata object or dict describing the source.
        """
        ...

    @abstractmethod
    def _build_type_data(self) -> Dict[str, Any]:
        """
        Construct source-specific type data used for persistence and registration responses.
        
        Subclasses must provide a dictionary containing the fields required to persist the source's type-specific configuration and to include in the registration response.
        
        Returns:
            type_data (dict): Mapping of source-type-specific keys and values to store on the DataSource and expose in the registered-source payload.
        """
        ...
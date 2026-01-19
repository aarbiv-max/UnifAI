"""Document registration implementation."""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Tuple
from functools import cached_property
from dataclasses import dataclass

from domain.registration.model import DocumentSourceData
from domain.data_source.repository import DataSourceRepository
from application.registration.base_registration import BaseRegistration
from application.validation.validator import Validator
from application.validation.validators.document import DocValidators
from global_utils.utils import secure_filename, compute_file_md5, cleanup_file


@dataclass
class DocumentMetadata:
    """Metadata for Document data sources used in pipeline execution."""
    doc_id: str
    doc_name: str = ""
    doc_path: str = ""
    upload_by: str = ""


class DocumentRegistration(BaseRegistration):
    """
    Registration flow for Document sources.
    
    Supports skip_validation flag:
    - When False (default): Full validation (extension, size, name, MD5)
      Used for external API calls that didn't pre-validate
    - When True: Only MD5 duplicate validation
      Used for UI uploads that pre-validated via /docs/validate endpoint
    """
    DATA_SOURCE_TYPE = "DOCUMENT"

    def __init__(
        self,
        data_source_repository: DataSourceRepository,
        upload_by: str,
        instance: Dict[str, Any],
        upload_folder: str,
        doc_validators: DocValidators,
        skip_validation: bool = False,
    ) -> None:
        """
        Initialize a DocumentRegistration that handles document source registration and validation.
        
        Creates a registration instance configured with where uploaded documents are stored and a validator derived from the provided DocValidators.
        
        Parameters:
            upload_folder (str): Filesystem directory where uploaded documents will be stored.
            doc_validators (DocValidators): Factory/source of validators used to construct the document validator.
            skip_validation (bool): If true, build validators that skip strict validation checks; otherwise enforce validation.
        
        """
        super().__init__(data_source_repository, upload_by, instance, skip_validation)
        self.upload_folder = upload_folder
        # Create validators based on skip_validation flag
        self._validator = Validator(doc_validators.create_validators(skip_validation))

    @cached_property
    def source_data(self) -> DocumentSourceData:
        # Get the original name for display purposes
        """
        Constructs a DocumentSourceData describing the uploaded document based on the registration instance and upload folder.
        
        Returns:
            DocumentSourceData: Object populated with `source_name`, generated `source_id`, generated `pipeline_id`, `doc_path`, file `md5`, and `form_data` extracted from the instance.
        """
        original_name = self.instance.get("source_name", "")
        # Use secure_filename to get the actual filename which matches what upload_docs() does when saving the file
        secure_name = secure_filename(original_name)
        path = os.path.join(self.upload_folder, secure_name)
        md5 = compute_file_md5(path)
        sid = str(uuid.uuid4())
        pid = f"document_{sid}"
        form_data = self.instance.get("metadata", {})
        return DocumentSourceData(
            source_name=original_name,
            source_id=sid,
            pipeline_id=pid,
            doc_path=path,
            md5=md5,
            form_data=form_data,
        )

    def run_validator(self) -> Tuple[bool, Dict[str, Any] | None]:
        """
        Validate the prepared document using the configured validator and produce a structured error payload on failure.
        
        On validation failure the uploaded file is removed. The returned error payload (when present) contains the following keys:
        - `doc_name`: original name of the document
        - `issue_type`: short error key (e.g., `"ValidationError"`)
        - `message`: human-readable message describing the failure
        - `validator`: name of the validator that produced the issue
        
        Returns:
            Tuple[bool, dict | None]: `True` and `None` if validation succeeds; `False` and an error dict if validation fails.
        """
        validation_args = {
            "doc_path": self.source_data.doc_path,
            "source_name": self.source_data.source_name,
            "md5": self.source_data.md5,
            "upload_by": self.upload_by,
        }
        is_valid, issue = self._validator.validate(**validation_args)

        if not is_valid:
            # Clean up the uploaded file since it failed validation
            cleanup_file(self.source_data.doc_path, "after validation failure")
            
            issue_key = (issue or {}).get("issue_key", "ValidationError")
            message = (issue or {}).get("message", "Validation error")
            validator_name = (issue or {}).get("validator_name", "Validator")
            return False, {
                "doc_name": self.source_data.source_name,
                "issue_type": issue_key,
                "message": message,
                "validator": validator_name,
            }

        return True, None

    def _build_metadata(self) -> DocumentMetadata:
        """
        Constructs a DocumentMetadata instance representing the uploaded document.
        
        Returns:
            DocumentMetadata: Metadata populated with `doc_id`, `doc_name`, and `doc_path` from the registration's computed source data, and `upload_by` set to the registration uploader.
        """
        return DocumentMetadata(
            doc_id=self.source_data.source_id,
            doc_name=self.source_data.source_name,
            doc_path=self.source_data.doc_path,
            upload_by=self.upload_by,
        )

    def _build_type_data(self) -> Dict[str, Any]:
        """
        Builds the document type payload describing file properties and form metadata for downstream processing.
        
        Returns:
            type_data (Dict[str, Any]): A dictionary containing:
                - `file_type`: file extension of the source document in lowercase.
                - `doc_path`: filesystem path to the stored document.
                - `page_count`: number of pages (defaults to 0).
                - `full_text`: extracted text (defaults to empty string).
                - `file_size`: size of the file in bytes (defaults to 0).
                - `md5`: MD5 checksum of the document.
                - any additional keys from the source document's `form_data`.
        """
        return {
            "file_type": self.source_data.source_name.rsplit(".", 1)[-1].lower(),
            "doc_path": self.source_data.doc_path,
            "page_count": 0,
            "full_text": "",
            "file_size": 0,
            "md5": self.source_data.md5,
            **self.source_data.form_data,
        }
"""
Pre-Upload Batch Validator for Document Files

This validator handles PRE-stage batch validation for document uploads.
It validates multiple files in a single call, with features specific to
pre-upload validation:

- Works with file metadata only (name, size) - no file content
- Tracks "pending" duplicates within the same batch (cross-file detection)
- Returns FileValidationResult with UI-friendly error format
- Does NOT perform MD5 content checking (requires actual file content)

Usage:
    from validator.doc_validators import DocValidators
    
    validators = DocValidators().create_validators(stage=ValidationStage.PRE)
    batch_validator = PreBatchValidator(validators, username="john_doe")
    result = batch_validator.validate_batch([
        {"name": "doc.pdf", "size": 1024000},
        {"name": "report.docx", "size": 2048000},
    ])
"""

from typing import Any, Dict, List
from dataclasses import dataclass

from common.interfaces import DataSourceValidator
from services.documents.name_duplicate_checker import NameDuplicateChecker
from utils.storage.mongo.mongo_helpers import get_mongo_storage
from shared.logger import logger


@dataclass
class FileValidationError:
    """Represents a validation error for a single file."""
    file_name: str
    error_type: str  # 'extension', 'size', 'duplicate'
    message: str


@dataclass 
class FileValidationResult:
    """Result of batch file validation."""
    valid_files: List[Dict[str, Any]]
    errors: List[FileValidationError]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid_files": self.valid_files,
            "errors": [
                {
                    "file_name": e.file_name,
                    "error_type": e.error_type,
                    "message": e.message
                }
                for e in self.errors
            ],
            "has_errors": len(self.errors) > 0
        }


# Mapping from validator names to error_type for UI display
VALIDATOR_ERROR_TYPE_MAP = {
    "ExtensionValidator": "extension",
    "SizeValidator": "size",
    "NameDuplicateValidator": "duplicate",
}


class PreBatchValidator:
    """
    Batch validator for PRE-stage document validation.
    
    This class extends the standard validator pattern to support:
    1. Batch validation of multiple files in one call
    2. Cross-file duplicate detection within the same batch
    3. UI-friendly FileValidationResult output format
    
    It uses the same individual validator classes as POST validation,
    but orchestrates them differently for the PRE use case.
    """
    
    def __init__(
        self, 
        validators: List[DataSourceValidator], 
        username: str,
        check_duplicates: bool = True
    ):
        """
        Initialize the batch validator.
        
        Args:
            validators: List of validators to run on each file
            username: Username for duplicate checking
            check_duplicates: Whether to check for duplicate filenames
        """
        self.validators = validators
        self.username = username
        self.check_duplicates = check_duplicates
        self.name_checker = NameDuplicateChecker(get_mongo_storage())
        
    def validate_batch(
        self, 
        files: List[Dict[str, Any]]
    ) -> FileValidationResult:
        """
        Validate a batch of files for upload.
        
        Args:
            files: List of file metadata dictionaries with 'name' and 'size' keys.
                   Example: [{"name": "doc.pdf", "size": 1024000}]
                   
        Returns:
            FileValidationResult containing valid files and errors.
        """
        valid_files: List[Dict[str, Any]] = []
        errors: List[FileValidationError] = []
        pending_normalized_names: set = set()
        
        # Fetch existing documents once for duplicate checking (batch optimization)
        existing_docs = (
            self.name_checker.get_existing_documents_for_user(self.username) 
            if self.check_duplicates else []
        )
        
        for file_info in files:
            filename = file_info.get("name", "")
            file_size = file_info.get("size", 0)
            
            # Track all validation errors for this file
            file_errors: List[FileValidationError] = []
            
            # Run each validator
            for validator in self.validators:
                # Build kwargs based on validator needs
                kwargs = {
                    "source_name": filename,
                    "file_size": file_size,
                    "upload_by": self.username,
                }
                
                is_valid, issue = validator.validate(**kwargs)
                
                if not is_valid and issue:
                    error_type = VALIDATOR_ERROR_TYPE_MAP.get(
                        issue.get("validator_name", ""),
                        "validation"
                    )
                    file_errors.append(FileValidationError(
                        file_name=filename,
                        error_type=error_type,
                        message=issue.get("message", "Validation failed")
                    ))
            
            # Check for cross-file duplicates within the same batch
            if self.check_duplicates and not file_errors:
                normalized_name = self.name_checker.normalize_filename(filename)
                
                if normalized_name in pending_normalized_names:
                    file_errors.append(FileValidationError(
                        file_name=filename,
                        error_type="duplicate",
                        message="A file with the same name is already selected for upload"
                    ))
            
            # Add to results
            if file_errors:
                errors.extend(file_errors)
            else:
                normalized_name = self.name_checker.normalize_filename(filename)
                pending_normalized_names.add(normalized_name)
                valid_files.append({
                    "name": filename,
                    "normalized_name": normalized_name,
                    "size": file_size
                })
        
        logger.info(
            f"Pre-batch validation complete for user {self.username}: "
            f"{len(valid_files)} valid, {len(errors)} errors"
        )
        
        return FileValidationResult(valid_files=valid_files, errors=errors)

"""
File Name Duplicate Validator

Validates that a file with the same normalized name doesn't already exist
for the user (unless the existing document has FAILED status).

This validator is used during registration for external API calls
(when skip_validation=False).
For UI uploads, name duplicate validation happens in /docs/validate before upload.

Note: This is different from the MD5 DuplicateValidator, which checks file content.
This validator checks file *names* to prevent ambiguity and confusion.

Rationale:
When a user defines a Retriever, they may filter documents based on file names
in order to reduce the scope of the retrieval operation. Allowing multiple files
with the same name uploaded by the same user would introduce ambiguity in this
filtering logic and make retrieval behavior unclear.

Therefore, we enforce uniqueness at the filter level:
{FILE_NAME}/{UPLOADED_BY} must be unique.
"""

from typing import Optional, Any, Tuple, Protocol


from domain.validation.port import DataSourceValidator
from domain.validation.model import ValidationIssue


class NameDuplicateCheckerPort(Protocol):
    """Port for name duplicate checking - implementations injected at runtime."""
    def is_duplicate_name(self, filename: str, username: str) -> Tuple[bool, Optional[str]]:
        """
        Determine whether a filename already exists for a given user and provide the existing document's status.
        
        Parameters:
            filename (str): Filename to check for duplication.
            username (str): Username under which to check for an existing document.
        
        Returns:
            Tuple[bool, Optional[str]]: First element is `True` if a document with the same filename exists for the user, `False` otherwise. Second element is the existing document's status (for example, `"FAILED"` or `"READY"`), or `None` if the status is unknown or not applicable.
        """
        ...


class NameDuplicateValidator(DataSourceValidator):
    """
    Validates that no document with the same normalized filename exists for the user.
    
    This validator:
    - Normalizes the filename using secure_filename
    - Checks if a document with the same normalized name exists for the user
    - Allows re-upload if the existing document has FAILED status
    
    This is different from MD5 duplicate checking - this checks names, not content.
    """
    name = "NameDuplicateValidator"
    error_message = "A document named '{source_name}' already exists (status: {status}). Please rename the file or delete the existing document."
    error_message_key = "Duplicate filename"

    def __init__(self, name_duplicate_checker: NameDuplicateCheckerPort) -> None:
        """
        Initialize the validator with a runtime-provided name duplicate checker.
        
        Parameters:
            name_duplicate_checker (NameDuplicateCheckerPort): Checker used at runtime to determine whether a filename is already present for the given user.
        """
        self._name_duplicate_checker = name_duplicate_checker

    def validate(self, **kwargs: Any) -> Tuple[bool, Optional[ValidationIssue]]:
        """
        Validate that the provided filename does not duplicate an existing document for the uploader.
        
        Parameters:
            source_name (str): Filename to check; if empty, validation passes.
            upload_by (str): Username of the uploader used to scope the duplicate check.
        
        Returns:
            tuple: `True` and `None` if the name is allowed; `False` and a `ValidationIssue` containing a formatted error message if a duplicate exists.
        """
        source_name = kwargs.get("source_name", "")
        upload_by = kwargs.get("upload_by", "")
        
        if not source_name:
            return True, None
        
        is_duplicate, status = self._name_duplicate_checker.is_duplicate_name(
            filename=source_name,
            username=upload_by
        )
        
        if is_duplicate:
            return False, self.build_issue(
                self.error_message.format(
                    source_name=source_name,
                    status=status or "unknown"
                )
            )
        
        return True, None
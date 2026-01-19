"""MD5 Duplicate Validator - checks for content duplicates."""
from typing import Optional, Any, Tuple, Protocol

from domain.validation.port import DataSourceValidator
from domain.validation.model import ValidationIssue


class DuplicateCheckerPort(Protocol):
    """Port for duplicate checking - implementations injected at runtime."""
    def is_duplicate(self, doc: dict) -> bool:
        """
        Determine whether the given document is a duplicate of an existing successfully processed file.
        
        Parameters:
            doc (dict): Document data used to determine duplication (e.g., content hash, source name, and other metadata).
        
        Returns:
            `True` if the document is a duplicate, `False` otherwise.
        """
        ...


class DuplicateValidator(DataSourceValidator):
    """Validates that the file content (MD5) is not a duplicate."""
    
    name = "DuplicateValidator"
    error_message = "This file appears to be a duplicate of an existing successfully processed file and was not added. File: {source_name}"
    error_message_key = "File duplicated error"

    def __init__(self, duplicate_checker: DuplicateCheckerPort) -> None:
        """
        Initialize the duplicate validator with a duplicate-checking port.
        
        Parameters:
            duplicate_checker (DuplicateCheckerPort): A runtime-provided component used to determine whether a document (represented as a dict) is a duplicate; stored for use during validation.
        """
        self._duplicate_checker = duplicate_checker

    def validate(self, **kwargs: Any) -> Tuple[bool, Optional[ValidationIssue]]:
        """
        Validate that the provided document is not a duplicate based on the injected duplicate checker.
        
        Parameters:
            **kwargs (dict): Document data passed to the duplicate checker; should include `source_name` when present for use in the error message.
        
        Returns:
            tuple: `(True, None)` if validation passes or an error occurred during duplicate checking; `(False, ValidationIssue)` when the document is detected as a duplicate.
        """
        try:
            if self._duplicate_checker.is_duplicate(kwargs):
                return False, self.build_issue(
                    self.error_message.format(source_name=kwargs.get("source_name"))
                )
        except Exception:
            return True, None

        return True, None
"""
File Extension Validator

Validates that uploaded files have supported extensions.
This validator is used during registration for external API calls
(when skip_validation=False).

For UI uploads, extension validation happens in /docs/validate before upload.
"""

from typing import Optional, Any, Tuple, List

from domain.validation.port import DataSourceValidator
from domain.validation.model import ValidationIssue


class ExtensionValidator(DataSourceValidator):
    """
    Validates file extension against supported types.
    
    This validator checks if the file extension is in the list of
    supported extensions.
    """
    name = "ExtensionValidator"
    error_message = "File type '.{extension}' is not supported. Supported types: {supported}"
    error_message_key = "Unsupported file type"

    def __init__(self, supported_extensions: List[str]) -> None:
        """
        Initialize the validator with allowed file extensions.
        
        Parameters:
            supported_extensions (List[str]): Allowed file extensions to validate against. Each entry should include the leading dot (e.g., '.pdf', '.jpg') and is compared against the file's lowercase extension.
        """
        self._supported_extensions = supported_extensions

    def validate(self, **kwargs: Any) -> Tuple[bool, Optional[ValidationIssue]]:
        """
        Check that the provided filename's extension is one of the supported extensions.
        
        If no filename is provided, validation is deferred (validator returns success so other validators may handle it).
        
        Parameters:
            source_name (str): The filename to validate; only the substring after the last `.` is used as the extension.
        
        Returns:
            A tuple where the first element is `True` if the extension is supported (or no filename was provided), `False` otherwise.
            The second element is a `ValidationIssue` describing the unsupported extension when the first element is `False`, otherwise `None`.
        """
        source_name = kwargs.get("source_name", "")
        
        if not source_name:
            return True, None  # No filename, let other validators handle
        
        # Extract extension
        extension = ""
        if "." in source_name:
            extension = source_name.rsplit(".", 1)[-1].lower()
        
        if not extension or f".{extension}" not in self._supported_extensions:
            supported_str = ", ".join(self._supported_extensions)
            return False, self.build_issue(
                self.error_message.format(
                    extension=extension or "unknown",
                    supported=supported_str
                )
            )
        
        return True, None
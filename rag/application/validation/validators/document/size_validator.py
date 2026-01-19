"""
File Size Validator

Validates that uploaded files don't exceed the maximum allowed size.
This validator is used during registration for external API calls
(when skip_validation=False).

For UI uploads, size validation happens in /docs/validate before upload.
"""

import os
from typing import Optional, Any, Tuple

from domain.validation.port import DataSourceValidator
from domain.validation.model import ValidationIssue


# Maximum file size in bytes (50 MB default)
DEFAULT_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


class SizeValidator(DataSourceValidator):
    """
    Validates file size against maximum allowed.
    
    This validator checks if the file size is within the configured
    maximum limit (50 MB by default).
    """
    name = "SizeValidator"
    error_message = "File size ({size_mb:.2f} MB) exceeds maximum allowed ({max_mb:.0f} MB)"
    error_message_key = "File too large"

    def __init__(self, max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES) -> None:
        """
        Initialize the SizeValidator with a maximum allowed file size.
        
        Parameters:
            max_file_size_bytes (int): Maximum file size in bytes. Defaults to 50 MB (50 * 1024 * 1024).
        """
        self._max_file_size_bytes = max_file_size_bytes

    def validate(self, **kwargs: Any) -> Tuple[bool, Optional[ValidationIssue]]:
        """
        Validate that a file at the provided path does not exceed the configured maximum size.
        
        If `doc_path` is missing, the path does not exist, or the file size cannot be determined, validation is skipped (passes) so other validators may handle those conditions.
        
        Parameters:
            doc_path (str, optional): Path to the uploaded file on disk, provided via kwargs.
        
        Returns:
            Tuple[bool, Optional[ValidationIssue]]: `True, None` if the file is within the allowed size or validation is skipped; `False, ValidationIssue` if the file size exceeds the configured maximum (issue message contains formatted size and limit).
        """
        doc_path = kwargs.get("doc_path", "")
        
        if not doc_path or not os.path.exists(doc_path):
            return True, None  # File doesn't exist, let other validators handle
        
        try:
            file_size = os.path.getsize(doc_path)
            
            if file_size > self._max_file_size_bytes:
                size_mb = file_size / (1024 * 1024)
                max_mb = self._max_file_size_bytes / (1024 * 1024)
                return False, self.build_issue(
                    self.error_message.format(size_mb=size_mb, max_mb=max_mb)
                )
        except Exception:
            # If we can't get file size, let it pass and fail elsewhere if needed
            return True, None
        
        return True, None
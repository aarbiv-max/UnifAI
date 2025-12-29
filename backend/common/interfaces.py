from typing import Optional, Dict, Any, TypedDict, Tuple
from enum import Enum


class ValidationStage(Enum):
    """
    Validation stage for document validation pipeline.
    
    PRE: Pre-upload validation (metadata only, batch mode, UI-friendly errors)
         - Uses file metadata (name, size) before files are uploaded
         - Supports batch validation with cross-file duplicate detection
         - Returns FileValidationResult for UI display
         
    POST: Post-upload validation (registration time, single item, has file content)
         - Uses actual file on disk (can compute MD5, read file size)
         - Single item validation during registration
         - Returns ValidationIssue format
    """
    PRE = "pre"
    POST = "post"


class ValidationIssue(TypedDict):
    """Structured validation failure returned by validators."""
    issue_key: str
    message: str
    validator_name: str


class DataSourceValidator:
    """Base contract for pre-execution validation with structured errors."""

    # Implementations should override these
    name: str = ""
    error_message: str = ""
    error_message_key: str = ""

    def validate(self, **kwargs: Any) -> Tuple[bool, Optional[ValidationIssue]]:
        """Validate before execution using keyword arguments.

        Return (True, None) if valid, otherwise (False, ValidationIssue).
        """
        ...
    def build_issue(self, message: Optional[str] = None) -> ValidationIssue:
        """Helper for implementations to build a structured ValidationIssue."""
        issue_message = message if message is not None else self.error_message
        return {
            "issue_key": self.error_message_key or "ValidationError",
            "message": issue_message,
            "validator_name": self.name or self.__class__.__name__,
        }

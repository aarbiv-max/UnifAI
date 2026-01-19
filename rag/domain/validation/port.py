"""Validation port - abstract interface for validators."""
from typing import Optional, Any, Tuple

from domain.validation.model import ValidationIssue


class DataSourceValidator:
    """Base contract for pre-execution validation with structured errors."""

    # Implementations should override these
    name: str = ""
    error_message: str = ""
    error_message_key: str = ""

    def validate(self, **kwargs: Any) -> Tuple[bool, Optional[ValidationIssue]]:
        """
        Perform pre-execution validation using provided keyword arguments.
        
        Subclasses should override to implement specific checks and return a structured result.
        
        Parameters:
            **kwargs (Any): Validator-specific inputs required to perform validation.
        
        Returns:
            Tuple[bool, Optional[ValidationIssue]]: `(True, None)` if validation passes; otherwise `(False, ValidationIssue)`.
        """
        ...

    def build_issue(self, message: Optional[str] = None) -> ValidationIssue:
        """
        Construct a structured ValidationIssue for this validator.
        
        Parameters:
            message (Optional[str]): Optional override for the validator's default error message.
        
        Returns:
            ValidationIssue: A mapping with keys:
                - "issue_key": the validator's `error_message_key` or "ValidationError" if not set.
                - "message": the provided `message` or the validator's `error_message`.
                - "validator_name": the validator's `name` or the validator class name.
        """
        issue_message = message if message is not None else self.error_message
        return {
            "issue_key": self.error_message_key or "ValidationError",
            "message": issue_message,
            "validator_name": self.name or self.__class__.__name__,
        }
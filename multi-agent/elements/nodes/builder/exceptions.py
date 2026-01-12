"""
Builder Node Exception Classes.

Custom exceptions for better error handling and debugging in the Builder Agent.
"""

from typing import Optional, Dict, Any

from .identifiers import BuilderPhase


class BuilderError(Exception):
    """Base exception for all builder-related errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class BuilderPhaseError(BuilderError):
    """Exception raised when a builder phase fails."""
    
    def __init__(
        self,
        phase: BuilderPhase,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.phase = phase
        self.cause = cause
        details = details or {}
        details["phase"] = phase.value
        super().__init__(message, details)
    
    def __str__(self) -> str:
        base = f"[Phase: {self.phase.value}] {self.message}"
        if self.cause:
            base += f" (caused by: {self.cause})"
        return base


class BuilderContextError(BuilderError):
    """Exception raised when builder context is invalid or missing."""
    
    def __init__(
        self,
        message: str = "Builder context not available",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)


class BuilderResourceError(BuilderError):
    """Exception raised when required resources are missing."""
    
    def __init__(
        self,
        resource_type: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.resource_type = resource_type
        message = message or f"Required resource not found: {resource_type}"
        details = details or {}
        details["resource_type"] = resource_type
        super().__init__(message, details)


class BuilderValidationError(BuilderError):
    """Exception raised when blueprint validation fails."""
    
    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.validation_errors = validation_errors or []
        details = details or {}
        if validation_errors:
            details["validation_errors"] = validation_errors
        super().__init__(message, details)


class BuilderToolError(BuilderError):
    """Exception raised when a builder tool fails."""
    
    def __init__(
        self,
        tool_name: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.tool_name = tool_name
        self.cause = cause
        details = details or {}
        details["tool_name"] = tool_name
        super().__init__(message, details)
    
    def __str__(self) -> str:
        base = f"[Tool: {self.tool_name}] {self.message}"
        if self.cause:
            base += f" (caused by: {self.cause})"
        return base


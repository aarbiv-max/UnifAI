"""
Builder context management.

Handles phase state and context for the builder agent.
"""

from .builder_context import (
    BuilderContext,
    BuilderState,
    AnalysisResult,
    ResourceSearchResult,
    DesignResult,
    ValidationResult,
)

__all__ = [
    "BuilderContext",
    "BuilderState",
    "AnalysisResult",
    "ResourceSearchResult",
    "DesignResult",
    "ValidationResult",
]


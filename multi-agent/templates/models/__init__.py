"""Template models package."""

from templates.models.template import (
    Template,
    TemplateSummary,
    PlaceholderMeta,
    PlaceholderPointer,
    ResourcePlaceholders,
    CategoryPlaceholders,
    TemplateMetadata,
    InputValidationResult,
    MaterializeResult,
)

__all__ = [
    # Template core models
    "Template",
    "TemplateSummary",
    "PlaceholderMeta",
    "PlaceholderPointer",
    "ResourcePlaceholders",
    "CategoryPlaceholders",
    "TemplateMetadata",
    # Result models
    "InputValidationResult",
    "MaterializeResult",
]

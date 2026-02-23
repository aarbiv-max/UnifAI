"""Docling DTOs (Data Transfer Objects)."""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import AliasChoices, AliasPath, BaseModel, Field
from global_utils.validators import CoercedStr


class DoclingOutputFormat(str, Enum):
    """Supported output formats for docling document conversion."""
    MARKDOWN = "md"
    TEXT = "text"


class DoclingOptions(BaseModel):
    """Options for document conversion."""
    to_formats: List[DoclingOutputFormat] = Field(
        default_factory=lambda: [DoclingOutputFormat.MARKDOWN, DoclingOutputFormat.TEXT]
    )
    image_export_mode: Optional[str] = None
    pdf_backend: Optional[str] = None


class DoclingRequest(BaseModel):
    """Request model for docling conversion."""
    file_path: Optional[str] = None
    url: Optional[str] = None
    options: DoclingOptions = Field(default_factory=DoclingOptions)


class DoclingResponse(BaseModel):
    """
    Response model for docling conversion.
    
    Handles multiple response formats using AliasChoices:
    - Direct fields: markdown, text, content
    - Nested document: document.md_content, document.text_content
    """
    markdown: CoercedStr = Field(
        default="",
        validation_alias=AliasChoices(
            "markdown",
            "md_content",
            AliasPath("document", "md_content"),
        )
    )
    text: CoercedStr = Field(
        default="",
        validation_alias=AliasChoices(
            "text",
            "text_content",
            "content",
            AliasPath("document", "text_content"),
        )
    )
    filename: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "filename",
            AliasPath("document", "filename"),
        )
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices(
            "metadata",
            AliasPath("document", "metadata"),
        )
    )
    
    @property
    def has_content(self) -> bool:
        """Check if the response contains any extractable content."""
        return bool(
            (self.markdown and self.markdown.strip()) or 
            (self.text and self.text.strip())
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {}
        if self.markdown:
            result["markdown"] = self.markdown
        if self.text:
            result["text"] = self.text
        if self.filename:
            result["filename"] = self.filename
        if self.metadata:
            result["metadata"] = self.metadata
        return result

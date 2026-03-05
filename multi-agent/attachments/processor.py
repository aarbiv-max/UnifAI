"""
Document processor for prompt attachments.

Phase 1 (naive): Extracts text content from PDF, DOCX, and MD files.
Supports both local Docling and a lightweight fallback for MD files.
"""

import os
import logging
from typing import Optional

from .models import ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Extracts plain text from uploaded documents.
    
    Uses Docling for PDF/DOCX and direct read for Markdown.
    """

    def __init__(self, docling_service=None):
        self._docling = docling_service

    def extract_text(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")

        if ext == ".md":
            return self._read_markdown(file_path)

        return self._convert_with_docling(file_path)

    def _read_markdown(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _convert_with_docling(self, file_path: str) -> str:
        if self._docling is None:
            raise RuntimeError(
                "Docling service is not configured. Cannot process PDF/DOCX files."
            )

        response = self._docling.process_file(file_path)

        # Prefer markdown output, fall back to text
        content = response.markdown or response.text
        if not content or not content.strip():
            raise ValueError(
                f"No text content could be extracted from {os.path.basename(file_path)}"
            )
        return content.strip()

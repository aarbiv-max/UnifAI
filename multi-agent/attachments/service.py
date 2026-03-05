"""
Attachment service – handles upload, processing, and prompt augmentation.

Phase 1 (naive): Files are saved to a temp directory, converted to text,
and the text is injected into the user prompt as context.
"""

import base64
import logging
import os
import tempfile
import uuid
from typing import Dict, List, Optional, Tuple

from .models import (
    Attachment,
    AttachmentContent,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
)
from .processor import DocumentProcessor

logger = logging.getLogger(__name__)


class AttachmentService:
    """Manages prompt attachment lifecycle: validate → store → extract text."""

    def __init__(self, processor: DocumentProcessor, upload_dir: Optional[str] = None):
        self._processor = processor
        self._upload_dir = upload_dir or os.path.join(tempfile.gettempdir(), "unifai_attachments")
        os.makedirs(self._upload_dir, exist_ok=True)

    # ── validation ──────────────────────────────────────────────────────

    def validate_files(
        self, files: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Validate a list of file dicts (name, size).
        Returns (valid_files, errors).
        """
        valid, errors = [], []
        for f in files:
            name = f.get("name", "")
            size = f.get("size", 0)
            ext = os.path.splitext(name)[1].lower()

            if ext not in ALLOWED_EXTENSIONS:
                errors.append({
                    "file_name": name,
                    "error_type": "extension",
                    "message": f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                })
            elif size > MAX_FILE_SIZE_BYTES:
                errors.append({
                    "file_name": name,
                    "error_type": "size",
                    "message": f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB",
                })
            else:
                valid.append(f)

        return valid, errors

    # ── upload + process ────────────────────────────────────────────────

    def process_attachments(
        self, files: List[Dict]
    ) -> List[AttachmentContent]:
        """
        Accept base64-encoded files, save to disk, extract text, clean up.
        
        Each file dict: {"name": str, "content": str (base64 data-url or raw)}
        Returns list of AttachmentContent with extracted text.
        """
        results: List[AttachmentContent] = []
        batch_dir = os.path.join(self._upload_dir, str(uuid.uuid4()))
        os.makedirs(batch_dir, exist_ok=True)

        try:
            for file_data in files:
                name = file_data["name"]
                content_b64 = file_data["content"]

                file_path = self._save_file(batch_dir, name, content_b64)
                try:
                    text = self._processor.extract_text(file_path)
                    ext = os.path.splitext(name)[1].lower()
                    results.append(AttachmentContent(
                        filename=name,
                        extension=ext,
                        text_content=text,
                        char_count=len(text),
                    ))
                except Exception as e:
                    logger.error(f"Failed to extract text from {name}: {e}")
                    raise
        finally:
            self._cleanup(batch_dir)

        return results

    # ── prompt augmentation ─────────────────────────────────────────────

    @staticmethod
    def build_augmented_prompt(
        user_prompt: str,
        attachments: List[AttachmentContent],
    ) -> str:
        """
        Combines extracted document text with the user prompt.
        Each attachment becomes a labeled context block.
        """
        if not attachments:
            return user_prompt

        parts = []
        for att in attachments:
            parts.append(
                f"[Attached document: {att.filename}]\n{att.text_content}"
            )

        context_block = "\n\n---\n\n".join(parts)
        return f"attached documents:\n{context_block}\n\nuser:\n{user_prompt}"

    # ── private helpers ─────────────────────────────────────────────────

    def _save_file(self, directory: str, filename: str, content_b64: str) -> str:
        """Decode base64 content and write to disk."""
        # Strip data-url prefix if present (e.g. "data:application/pdf;base64,...")
        if "," in content_b64:
            content_b64 = content_b64.split(",", 1)[1]

        file_bytes = base64.b64decode(content_b64)
        file_path = os.path.join(directory, filename)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        logger.info(f"Saved attachment: {filename} ({len(file_bytes)} bytes)")
        return file_path

    @staticmethod
    def _cleanup(directory: str) -> None:
        """Remove temporary files after processing."""
        try:
            for f in os.listdir(directory):
                os.remove(os.path.join(directory, f))
            os.rmdir(directory)
        except Exception as e:
            logger.warning(f"Cleanup failed for {directory}: {e}")

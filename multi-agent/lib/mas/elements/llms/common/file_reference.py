"""
FileReference — immutable domain model for uploaded file metadata.

Represents a file hosted on an external provider (e.g. Google Gemini File API).
Only the lightweight URI is stored; the actual bytes live on the provider's servers.
"""
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)

FILE_EXPIRY_HOURS: int = 47
FILE_PROCESSING_TIMEOUT_S: int = 120
DEFAULT_ALLOWED_MIME_TYPES: list = [
    "application/pdf",
    "text/plain",
    "text/csv",
    "text/html",
    "text/markdown",
]


class FileState(str, Enum):
    PROCESSING = "processing"
    ACTIVE = "active"
    FAILED = "failed"


class FileReference(BaseModel):
    """Immutable reference to an uploaded file."""

    model_config = ConfigDict(frozen=True)

    file_uri: str
    mime_type: str
    display_name: str
    size_bytes: int
    state: FileState = FileState.ACTIVE
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @classmethod
    def from_dicts(
        cls, data: Optional[List[dict]],
    ) -> Optional[List["FileReference"]]:
        """Defensive deserialization — skips malformed entries."""
        if not data:
            return None
        refs: List[FileReference] = []
        for i, d in enumerate(data):
            try:
                refs.append(cls(**d))
            except (ValidationError, TypeError, KeyError) as exc:
                logger.warning(
                    "Skipping malformed FileReference at index %d: %s", i, exc,
                )
        return refs or None

    @staticmethod
    def to_dicts(refs: Optional[List["FileReference"]]) -> List[dict]:
        """Serialize to JSON-safe dicts (datetime → ISO 8601)."""
        return [r.model_dump(mode="json") for r in refs] if refs else []

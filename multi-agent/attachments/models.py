from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@dataclass(frozen=True)
class Attachment:
    """Metadata for a file attached to a prompt."""
    filename: str
    extension: str
    size_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AttachmentContent:
    """Processed attachment with extracted text content."""
    filename: str
    extension: str
    text_content: str
    char_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

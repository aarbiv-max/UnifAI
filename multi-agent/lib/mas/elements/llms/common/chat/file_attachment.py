from typing import Any

from pydantic import BaseModel, ConfigDict

FILE_ATTACHMENT_TTL_HOURS = 48


def get_attachment_field(att: Any, key: str, default: str = "") -> str:
    """Read a field from a dict or Pydantic object uniformly.

    File attachments travel through the system as both ``FileAttachment``
    model instances (in graph state) and plain dicts (in workspace
    variables after serialisation).  This helper allows callers to read
    fields without caring about the concrete representation.
    """
    if isinstance(att, dict):
        return att.get(key, default)
    return getattr(att, key, default)


class FileAttachment(BaseModel):
    """Immutable reference to a file uploaded via an external file service."""

    file_name: str
    mime_type: str
    file_uri: str
    size_bytes: int
    uploaded_at: str

    model_config = ConfigDict(frozen=True)

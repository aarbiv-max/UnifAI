from pydantic import BaseModel, ConfigDict


class FileAttachment(BaseModel):
    """Immutable reference to a file uploaded via an external file service."""

    file_name: str
    mime_type: str
    file_uri: str
    size_bytes: int
    upload_status: str = "completed"
    uploaded_at: str

    model_config = ConfigDict(frozen=True)

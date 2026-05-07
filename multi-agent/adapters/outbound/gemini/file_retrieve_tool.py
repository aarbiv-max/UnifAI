from typing import Any, List

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from mas.elements.tools.common.base_tool import BaseTool


class GeminiFileRetrieveArgs(BaseModel):
    file_uri: str = Field(
        ...,
        description=(
            "The Gemini File URI of the attached file from the workspace facts. "
            "Copy it exactly as shown."
        ),
    )
    instruction: str = Field(
        default="Extract and return the complete text content of this document.",
        description="Instruction for how to process the file (extract text, summarize, extract tables, etc.)",
    )


class GeminiFileRetrieveTool(BaseTool):
    """Reads or analyzes a user-attached file using its Gemini File URI."""

    name: str = "read_attached_file"
    description: str = (
        "Read or analyze a user-attached file. Use the file_uri exactly as shown "
        "in the workspace facts: 'Attached file: name.pdf (mime_type) -> <URI>'. "
        "Copy the full URI that starts with 'https://generativelanguage.googleapis.com/'."
    )
    args_schema = GeminiFileRetrieveArgs

    def __init__(self, api_key: str, model_name: str, file_attachments: List[dict] = None):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        self._file_attachments = file_attachments or []

    @staticmethod
    def _get_field(obj, key: str, default: str = "") -> str:
        """Read a field from a dict or object attribute uniformly."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _resolve_attachment(self, file_uri: str) -> dict | None:
        """Find attachment by URI, return it or None."""
        for att in self._file_attachments:
            if self._get_field(att, "file_uri") == file_uri:
                return att
        return None

    def run(self, **kwargs: Any) -> Any:
        args = GeminiFileRetrieveArgs(**kwargs)

        attachment = self._resolve_attachment(args.file_uri)
        if not attachment:
            valid_uris = [
                self._get_field(a, "file_uri") for a in self._file_attachments
            ]
            return {
                "success": False,
                "error": (
                    f"Invalid file_uri '{args.file_uri}'. "
                    f"Use one of the exact URIs from workspace facts: {valid_uris}"
                ),
            }

        mime_type = self._get_field(attachment, "mime_type", "application/octet-stream")

        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=[
                    types.Part.from_uri(file_uri=args.file_uri, mime_type=mime_type),
                    args.instruction,
                ],
            )
            return {"success": True, "content": response.text}
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "expired" in error_msg or "404" in error_msg:
                return {
                    "success": False,
                    "error": (
                        "File has expired and is no longer available. "
                        "Gemini files expire after 48 hours. "
                        "Ask the user to re-attach the file."
                    ),
                }
            return {"success": False, "error": f"Failed to retrieve file: {e}"}

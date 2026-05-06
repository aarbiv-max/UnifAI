import logging
from typing import Any

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from mas.elements.tools.common.base_tool import BaseTool

logger = logging.getLogger(__name__)


class GeminiFileRetrieveArgs(BaseModel):
    file_uri: str = Field(
        ...,
        description="The Gemini File URI to retrieve content from (e.g. 'files/abc123')",
    )
    instruction: str = Field(
        default="Extract and return the complete text content of this document.",
        description="Instruction for how to process the file (extract text, summarize, extract tables, etc.)",
    )


class GeminiFileRetrieveTool(BaseTool):
    """Reads or analyzes an attached file via Gemini's generate_content API."""

    name: str = "read_attached_file"
    description: str = (
        "Read or analyze an attached file using its Gemini File URI. "
        "Provide the file_uri from the workspace and optionally an instruction "
        "for how to process the file (extract text, summarize, extract tables, etc.)."
    )
    args_schema = GeminiFileRetrieveArgs

    def __init__(self, api_key: str, model_name: str):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def run(self, **kwargs: Any) -> Any:
        args = GeminiFileRetrieveArgs(**kwargs)
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=[
                    types.Part.from_uri(file_uri=args.file_uri, mime_type="*/*"),
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
                        f"File '{args.file_uri}' has expired and is no longer available. "
                        "Gemini files expire after 48 hours. "
                        "Ask the user to re-attach the file if further document analysis is needed."
                    ),
                }
            return {"success": False, "error": f"Failed to retrieve file: {e}"}

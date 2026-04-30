"""
GeminiFileUploader — outbound adapter implementing FileUploader for the
Google Gemini File API.

Handles parallel uploads, per-file retry, and polling for ACTIVE state.
"""
import io
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from typing import Any, Dict, List, Tuple

from tenacity import retry, stop_after_attempt, wait_exponential

from mas.elements.llms.common.file_reference import (
    FILE_PROCESSING_TIMEOUT_S,
    FileReference,
    FileState,
)
from mas.elements.llms.common.file_uploader import FileUploader

logger = logging.getLogger(__name__)

_MAX_WORKERS = 3
_POLL_BASE_S = 2.0
_POLL_CAP_S = 15.0
_POLL_MULTIPLIER = 1.5


class GeminiFileUploader(FileUploader):
    """Uploads files to Google's Gemini File API and polls until ACTIVE."""

    def __init__(self) -> None:
        gunicorn_timeout = os.environ.get("GUNICORN_TIMEOUT")
        if gunicorn_timeout and int(gunicorn_timeout) < 180:
            logger.warning(
                "GUNICORN_TIMEOUT=%s is below 180s. File uploads may time "
                "out under load (upload pipeline can take up to 120s + "
                "network overhead).",
                gunicorn_timeout,
            )

    def upload_batch(
        self,
        files: List[Tuple[str, bytes, str]],
        credentials: Dict[str, Any],
    ) -> Tuple[List[FileReference], List[Dict[str, str]]]:
        """Upload files to Gemini, poll for ACTIVE, return refs + errors."""
        from google import genai

        api_key = credentials["api_key"]
        client = genai.Client(api_key=api_key)

        if len(files) == 1:
            filename, content, mime_type = files[0]
            try:
                ref = self._upload_single(client, filename, content, mime_type)
                return [ref], []
            except Exception as exc:
                logger.error("Upload failed for %s: %s", filename, exc)
                return [], [{"filename": filename, "error": str(exc)}]

        refs: List[FileReference] = []
        errors: List[Dict[str, str]] = []
        futures = {}

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            for filename, content, mime_type in files:
                future = pool.submit(
                    self._upload_single, client, filename, content, mime_type,
                )
                futures[future] = filename

            done, not_done = wait(
                futures, timeout=FILE_PROCESSING_TIMEOUT_S,
            )

            for future in not_done:
                fname = futures[future]
                future.cancel()
                errors.append({"filename": fname, "error": "Upload timed out"})

            for future in done:
                fname = futures[future]
                try:
                    refs.append(future.result())
                except Exception as exc:
                    logger.error("Upload failed for %s: %s", fname, exc)
                    errors.append({"filename": fname, "error": str(exc)})

        if not refs and errors:
            raise RuntimeError(
                f"All {len(errors)} file(s) failed to upload: "
                + "; ".join(e["error"] for e in errors)
            )
        return refs, errors

    def _upload_single(
        self, client: Any, filename: str, content: bytes, mime_type: str,
    ) -> FileReference:
        """Upload one file with retry, then poll until ACTIVE."""
        uploaded = self._upload_with_retry(client, filename, content, mime_type)
        active_file = self._wait_for_active(client, uploaded)
        return FileReference(
            file_uri=active_file.uri,
            mime_type=active_file.mime_type or mime_type,
            display_name=active_file.display_name or filename,
            size_bytes=len(content),
            state=FileState.ACTIVE,
        )

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _upload_with_retry(
        client: Any, filename: str, content: bytes, mime_type: str,
    ) -> Any:
        """Upload file bytes to Gemini with automatic retry."""
        file_obj = io.BytesIO(content)
        file_obj.name = filename
        return client.files.upload(
            file=file_obj,
            config={"mime_type": mime_type, "display_name": filename},
        )

    @staticmethod
    def _wait_for_active(client: Any, uploaded_file: Any) -> Any:
        """Adaptive polling until file reaches ACTIVE state."""
        delay = _POLL_BASE_S
        deadline = time.monotonic() + FILE_PROCESSING_TIMEOUT_S

        while time.monotonic() < deadline:
            file_info = client.files.get(name=uploaded_file.name)
            state_str = str(getattr(file_info, "state", "")).upper()
            if "ACTIVE" in state_str:
                return file_info
            if "FAILED" in state_str:
                raise RuntimeError(
                    f"File {uploaded_file.name} failed processing on Google's servers"
                )
            time.sleep(delay)
            delay = min(delay * _POLL_MULTIPLIER, _POLL_CAP_S)

        raise TimeoutError(
            f"File {uploaded_file.name} did not reach ACTIVE within "
            f"{FILE_PROCESSING_TIMEOUT_S}s"
        )

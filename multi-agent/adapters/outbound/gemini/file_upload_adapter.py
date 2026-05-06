import io
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from google import genai
from google.genai import types as genai_types
from google.api_core.exceptions import (
    ResourceExhausted,
    ServiceUnavailable,
    InternalServerError,
)

from mas.session.execution.ports import (
    IFileUploadService,
    FileUploadRequest,
    FileUploadResult,
    FileUploadError,
)

logger = logging.getLogger(__name__)

RETRIABLE_EXCEPTIONS = (
    ResourceExhausted,
    ServiceUnavailable,
    InternalServerError,
    ConnectionError,
    TimeoutError,
)
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_MULTIPLIER = 2.0


class GeminiFileUploadAdapter(IFileUploadService):
    """Uploads files to Gemini File API with parallel execution and atomic rollback."""

    def __init__(self, api_key: str, max_workers: int = 3):
        self._client = genai.Client(api_key=api_key)
        self._max_workers = max_workers

    def upload_batch(self, files: List[FileUploadRequest]) -> List[FileUploadResult]:
        uploaded = []
        try:
            with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
                futures = {
                    pool.submit(self._upload_single_with_retry, f): i
                    for i, f in enumerate(files)
                }
                results_by_index = {}
                for future in as_completed(futures):
                    idx = futures[future]
                    resp = future.result()
                    uploaded.append(resp)
                    results_by_index[idx] = resp

            return [
                FileUploadResult(
                    file_name=files[i].file_name,
                    mime_type=files[i].mime_type,
                    file_uri=results_by_index[i].uri,
                    size_bytes=len(files[i].file_bytes),
                )
                for i in range(len(files))
            ]
        except Exception as e:
            for resp in uploaded:
                try:
                    self._client.files.delete(name=resp.name)
                except Exception:
                    logger.warning("Rollback: failed to delete %s", resp.name)
            raise FileUploadError(
                message=f"File upload failed: {type(e).__name__}: {e}",
                retriable=isinstance(e, RETRIABLE_EXCEPTIONS),
            ) from e

    def _upload_single_with_retry(self, f: FileUploadRequest):
        last_exception = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                return self._upload_single(f)
            except RETRIABLE_EXCEPTIONS as e:
                last_exception = e
                if attempt < MAX_RETRIES:
                    delay = BACKOFF_BASE_SECONDS * (BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(
                        "Upload attempt %d/%d for '%s' failed (%s), retrying in %.1fs",
                        attempt + 1, MAX_RETRIES + 1, f.file_name,
                        type(e).__name__, delay,
                    )
                    time.sleep(delay)
        raise last_exception

    def _upload_single(self, f: FileUploadRequest):
        file_obj = io.BytesIO(f.file_bytes)
        file_obj.name = f.file_name
        return self._client.files.upload(
            file=file_obj,
            config=genai_types.UploadFileConfig(
                mime_type=f.mime_type,
                display_name=f.file_name,
            ),
        )

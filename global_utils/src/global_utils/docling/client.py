"""
Docling HTTP Client - Pure transport layer.

This client handles only HTTP communication with the docling service.
Business logic, validation, and error transformation are in the service layer.

Uses the async submit + poll + fetch pattern to avoid holding a single
HTTP connection open during long conversions (which gets killed by
intermediate load balancers / proxies with idle-connection timeouts).
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List

import httpx

from global_utils.docling.exceptions import (
    DoclingConnectionError,
    DoclingTimeoutError,
)

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 10


class DoclingClient:
    """
    Pure HTTP client for docling service.
    
    Handles only transport concerns:
    - HTTP requests/responses
    - Connection management
    - Timeout handling
    
    File conversion uses the async API internally (submit + poll + fetch)
    so that no single HTTP connection is held idle for longer than the
    poll interval.

    Example:
        client = DoclingClient(
            base_url="http://docling-service:5001",
            timeout=300,
        )
        raw_response = client.post_file("/path/to/doc.pdf", options={...})
    """
    
    def __init__(
        self, 
        base_url: str,
        timeout: int = 300,
    ):
        """
        Initialize the HTTP client.
        
        Args:
            base_url: Base URL for the docling service
            timeout: Total wall-clock timeout in seconds for a full
                     submit + poll + fetch cycle
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(60),
        )
        logger.info(f"DoclingClient initialized: {self.base_url}, timeout={self.timeout}s")
    
    def post_file(
        self, 
        file_path: str, 
        to_formats: List[str],
        image_export_mode: Optional[str] = None,
        pdf_backend: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert a file via the docling service.
        
        Internally uses the async API: submit the file, poll for completion,
        then fetch the result.  Each individual HTTP request is short-lived
        so intermediate proxies / load balancers won't drop the connection.
        
        Args:
            file_path: Path to the file to convert
            to_formats: List of output formats (e.g., ["md", "text"])
            image_export_mode: Mode for image export (e.g., "placeholder")
            pdf_backend: PDF parsing backend (e.g., "dlparse_v4")
        
        Returns:
            Raw JSON response from the service
            
        Raises:
            DoclingConnectionError: If service is unreachable or conversion fails
            DoclingTimeoutError: If the total timeout is exceeded
        """
        task_id = self._submit_file(file_path, to_formats, image_export_mode, pdf_backend)
        self._poll_until_done(task_id)
        return self._fetch_result(task_id)

    def _submit_file(
        self,
        file_path: str,
        to_formats: List[str],
        image_export_mode: Optional[str] = None,
        pdf_backend: Optional[str] = None,
    ) -> str:
        """Submit a file for async conversion, return the task_id."""
        url = "/v1/convert/file/async"

        try:
            with open(file_path, 'rb') as f:
                multipart_data = [
                    ('files', (os.path.basename(file_path), f, 'application/octet-stream')),
                ]

                for fmt in to_formats:
                    multipart_data.append(('to_formats', (None, fmt)))

                if image_export_mode:
                    multipart_data.append(('image_export_mode', (None, image_export_mode)))

                if pdf_backend:
                    multipart_data.append(('pdf_backend', (None, pdf_backend)))

                response = self._client.post(url, files=multipart_data)
                response.raise_for_status()
                data = response.json()

            task_id = data.get("task_id")
            if not task_id:
                raise DoclingConnectionError(
                    f"Async submit succeeded but response has no task_id: {data}"
                )
            logger.info(f"Docling async task submitted: task_id={task_id}")
            return task_id

        except httpx.ConnectError as e:
            raise DoclingConnectionError(f"Cannot connect to docling service: {e}")
        except httpx.TimeoutException as e:
            raise DoclingTimeoutError(f"Submit request timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise DoclingConnectionError(f"HTTP error {e.response.status_code}: {e}")
        except httpx.TransportError as e:
            raise DoclingConnectionError(f"Transport error during submit: {e}")
        except (DoclingConnectionError, DoclingTimeoutError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in _submit_file: {e}", exc_info=True)
            raise

    def _poll_until_done(self, task_id: str) -> None:
        """Poll the task status until success, failure, or timeout."""
        deadline = time.monotonic() + self.timeout

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DoclingTimeoutError(
                    f"Docling conversion timed out after {self.timeout}s (task_id={task_id})"
                )

            try:
                response = self._client.get(f"/v1/status/poll/{task_id}")
                response.raise_for_status()
                data = response.json()
            except httpx.ConnectError as e:
                raise DoclingConnectionError(f"Cannot connect to docling service: {e}")
            except httpx.TimeoutException as e:
                raise DoclingTimeoutError(f"Poll request timed out: {e}")
            except httpx.HTTPStatusError as e:
                raise DoclingConnectionError(f"HTTP error {e.response.status_code}: {e}")
            except httpx.TransportError as e:
                raise DoclingConnectionError(f"Transport error during poll: {e}")
            except Exception as e:
                logger.error(f"Unexpected error polling task {task_id}: {e}", exc_info=True)
                raise

            status = data.get("task_status", "").lower()
            logger.info(f"Docling task {task_id}: status={status}")

            if status == "success":
                return
            if status == "failure":
                error_msg = data.get("error_message", "unknown error")
                raise DoclingConnectionError(
                    f"Docling conversion failed (task_id={task_id}): {error_msg}"
                )

            time.sleep(min(_POLL_INTERVAL_SECONDS, remaining))

    def _fetch_result(self, task_id: str) -> Dict[str, Any]:
        """Fetch the conversion result for a completed task."""
        try:
            response = self._client.get(f"/v1/result/{task_id}")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise DoclingConnectionError(f"Cannot connect to docling service: {e}")
        except httpx.TimeoutException as e:
            raise DoclingTimeoutError(f"Fetch result timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise DoclingConnectionError(f"HTTP error {e.response.status_code}: {e}")
        except httpx.TransportError as e:
            raise DoclingConnectionError(f"Transport error fetching result: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching result for {task_id}: {e}", exc_info=True)
            raise

    def post_url(
        self, 
        document_url: str, 
        to_formats: List[str],
        image_export_mode: Optional[str] = None,
        pdf_backend: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST a URL to the docling service for conversion.
        
        Args:
            document_url: URL of the document to convert
            to_formats: List of output formats
            image_export_mode: Mode for image export
            pdf_backend: PDF parsing backend
        
        Returns:
            Raw JSON response from the service
            
        Raises:
            DoclingConnectionError: If service is unreachable
            DoclingTimeoutError: If request times out
        """
        url = "/v1/convert/source"
        
        try:
            payload = {
                "sources": [{"kind": "http", "url": document_url}],
                "to_formats": to_formats
            }
            
            if image_export_mode:
                payload["image_export_mode"] = image_export_mode
            
            if pdf_backend:
                payload["pdf_backend"] = pdf_backend
            
            response = self._client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json", "accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.ConnectError as e:
            raise DoclingConnectionError(f"Cannot connect to docling service: {e}")
        except httpx.TimeoutException as e:
            raise DoclingTimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise DoclingConnectionError(f"HTTP error {e.response.status_code}: {e}")
        except httpx.TransportError as e:
            raise DoclingConnectionError(f"Transport error communicating with docling service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in post_url: {e}", exc_info=True)
            raise

    def health_check(self) -> bool:
        """
        Check if the docling service is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self._client.get("/health", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

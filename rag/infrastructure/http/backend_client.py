"""HTTP client for the platform-backend service.

Provides typed methods for each API call RAG needs to make
to the platform-backend.  Add new methods here as new endpoints
are consumed.
"""
import requests
from typing import Any, Dict, Optional

from shared.logger import logger


class BackendClient:
    """General HTTP client for the platform-backend."""

    def __init__(self, base_url: str, timeout: int = 10):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # ──────────────────── Admin Config ─────────────────────────────────────

    def get_slack_channel_restrictions(self) -> Optional[Dict[str, Any]]:
        """
        Fetch the slack channel restriction rules from admin config.

        Returns:
            Dict with keys restricted_prefixes, restricted_suffixes,
            restricted_keywords — or None on failure.
            Values already include defaults if nothing is stored in DB.
        """
        try:
            resp = requests.get(
                f"{self._base_url}/api/admin_config/config.get",
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            for category in data.get("categories", []):
                for section in category.get("sections", []):
                    if section["key"] == "slack_channel_restrictions":
                        return {
                            f["key"]: f["value"]
                            for f in section.get("fields", [])
                        }

            return None

        except Exception:
            logger.exception("Failed to fetch channel restrictions from platform-backend")
            return None

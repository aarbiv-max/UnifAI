"""Shared naming utilities for sandbox components."""
import re

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9\-]")


def sanitize_name(raw: str) -> str:
    """Sanitize a string for use in container/worktree/branch names."""
    return _SAFE_NAME_RE.sub("-", raw).strip("-").lower() or "default"

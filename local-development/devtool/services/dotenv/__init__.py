"""Environment file management — re-exports for backward compatibility."""

from .common import GenerateResult, is_auto_generate
from .display import show
from .generator import generate, generate_all
from .inspector import (
    check_auto_generate,
    check_missing_keys,
    check_placeholders,
    check_unresolved,
    collect_auto_generate_keys,
)
from .local_auth import align_local_auth
from .resolver import (
    get_or_create_shared_secret,
    replace_env_value,
    resolve_auto_generate_key,
)

__all__ = [
    "GenerateResult",
    "align_local_auth",
    "check_auto_generate",
    "check_missing_keys",
    "check_placeholders",
    "check_unresolved",
    "collect_auto_generate_keys",
    "generate",
    "generate_all",
    "get_or_create_shared_secret",
    "is_auto_generate",
    "replace_env_value",
    "resolve_auto_generate_key",
    "show",
]

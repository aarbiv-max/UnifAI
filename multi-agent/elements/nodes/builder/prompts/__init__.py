"""
Builder prompts module.

Centralized location for all LLM instructions used by the Builder Agent.
Follows the codebase pattern of separating prompts from business logic.
"""

from .system import BUILDER_SYSTEM_MESSAGE, build_system_message
from .phases import (
    ANALYZE_PHASE_GUIDANCE,
    SEARCH_PHASE_GUIDANCE,
    DESIGN_PHASE_GUIDANCE,
    VALIDATE_PHASE_GUIDANCE,
    build_analyze_prompt,
    build_search_prompt,
    build_design_prompt,
    build_validate_prompt,
)

__all__ = [
    # System message
    "BUILDER_SYSTEM_MESSAGE",
    "build_system_message",
    # Phase guidance (static)
    "ANALYZE_PHASE_GUIDANCE",
    "SEARCH_PHASE_GUIDANCE",
    "DESIGN_PHASE_GUIDANCE",
    "VALIDATE_PHASE_GUIDANCE",
    # Phase prompts (dynamic)
    "build_analyze_prompt",
    "build_search_prompt",
    "build_design_prompt",
    "build_validate_prompt",
]

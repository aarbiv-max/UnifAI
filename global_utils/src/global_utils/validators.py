"""
Pydantic validators and custom type aliases.

This module provides reusable validators and type annotations for Pydantic models,
particularly useful when handling API responses with nullable fields.
"""
from __future__ import annotations
from typing import Any, Annotated
from pydantic import BeforeValidator


def coerce_to_str(v: Any) -> str:
    """
    Convert None or non-string values to empty string.
    
    Useful as a Pydantic BeforeValidator when API responses may return null
    for string fields.
    
    Args:
        v: Any value to convert
        
    Returns:
        Empty string if v is None, otherwise str(v)
    """
    if v is None:
        return ""
    return str(v)


# Type alias for Pydantic string fields that should coerce None to empty string
CoercedStr = Annotated[str, BeforeValidator(coerce_to_str)]


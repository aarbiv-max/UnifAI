"""
Statistics module constants.

This module centralizes constants and helper functions used within the statistics module.
"""

from typing import Optional


# =============================================================================
# TIME RANGE MAPPING CONSTANTS
# =============================================================================

# All valid time_range string values
VALID_TIME_RANGES = ["today", "7days", "30days", "all"]

# Mapping from number of days to time_range string values
DAYS_TO_TIME_RANGE: dict[int, str] = {
    1: "today",
    7: "7days",
    30: "30days"
}


def days_to_time_range(days: int) -> Optional[str]:
    """
    Convert number of days to time_range string.
    
    Currently supported mappings:
    - 1 day → "today"
    - 7 days → "7days"
    - 30 days → "30days"
    
    Note: The system currently only supports these three time ranges plus "all".
    Other day values return None and require custom filter handling.
    
    Args:
        days: Number of days to look back (currently only 1, 7, or 30 are used)
    
    Returns:
        Time range string or None if days doesn't match a supported value
    """
    return DAYS_TO_TIME_RANGE.get(days)


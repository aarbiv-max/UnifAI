"""
Analytics utility functions for time range filtering and date calculations.

This module provides reusable utilities for:
- Time range filtering (today, 7days, 30days, all)
- Cutoff date calculations
- Query filter building for time-based analytics
- Time series aggregation pipelines
"""

import copy
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta, timezone


def apply_time_range_filter(
    filter_dict: Dict[str, Any], 
    time_range: Optional[str],
    field_path: str = "run_context.started_at"
) -> Dict[str, Any]:
    """
    Apply time range filtering to a filter dictionary.
    
    Args:
        filter_dict: Base filter dictionary
        time_range: Optional time filter - "today", "7days", "30days", or "all"
        field_path: Field path to filter on (default: "run_context.started_at")
        
    Returns:
        Filter dictionary with time range applied if specified
    """
    result = copy.deepcopy(filter_dict) if filter_dict else {}
    
    if time_range and time_range != "all":
        cutoff_date = get_cutoff_date(time_range)
        cutoff_iso = cutoff_date.isoformat().replace('+00:00', 'Z')
        result[field_path] = {"$gte": cutoff_iso}

    return result


def get_cutoff_date(time_range: str) -> Optional[datetime]:
    """
    Get cutoff date based on time_range string.
    
    Args:
        time_range: One of "today", "7days", "30days", or "all"
    
    Returns:
        Cutoff datetime in UTC, or None for "all" (no time limit)
    """
    now = datetime.now(timezone.utc)
    
    if time_range == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "7days":
        return now - timedelta(days=7)
    elif time_range == "30days":
        return now - timedelta(days=30)
    else:
        # "all" means no time limit - return None
        return None


def get_time_range_params(time_range: str, now: datetime) -> Tuple[Optional[datetime], str]:
    """
    Get cutoff date and date format based on time_range.
    
    Args:
        time_range: One of "today", "7days", "30days", or "all"
        now: Current datetime (usually datetime.now(timezone.utc))
    
    Returns:
        Tuple of (cutoff_date, date_format_string). cutoff_date is None for "all".
    """
    if time_range == "today":
        cutoff_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        date_format = "%Y-%m-%d %H:00"
    elif time_range == "7days":
        cutoff_date = now - timedelta(days=7)
        date_format = "%Y-%m-%d"
    elif time_range == "30days":
        cutoff_date = now - timedelta(days=30)
        date_format = "%Y-%m-%d"
    else:
        # "all" means no time limit - use monthly granularity for readability
        cutoff_date = None
        date_format = "%Y-%m"  # Year-Month format for better grouping of all-time data
    
    return cutoff_date, date_format


def build_time_series_pipeline(
    cutoff_iso: Optional[str],
    date_format: str,
    field_path: str = "run_context.started_at"
) -> List[Dict[str, Any]]:
    """
    Build MongoDB aggregation pipeline for time series data.
    
    Args:
        cutoff_iso: ISO format cutoff date string, or None for no time limit
        date_format: strftime format for grouping (e.g., "%Y-%m-%d")
        field_path: Field to use for time filtering
    
    Returns:
        MongoDB aggregation pipeline
    """
    # Build match stage - only filter by time if cutoff is provided
    if cutoff_iso:
        match_stage = {"$match": {
            field_path: {"$gte": cutoff_iso, "$exists": True}
        }}
    else:
        # No time limit - just ensure the field exists
        match_stage = {"$match": {
            field_path: {"$exists": True}
        }}
    
    return [
        match_stage,
        {"$group": {
            "_id": {
                "$dateToString": {
                    "format": date_format,
                    "date": {"$dateFromString": {"dateString": f"${field_path}"}}
                }
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}},
        {"$limit": 1000}
    ]

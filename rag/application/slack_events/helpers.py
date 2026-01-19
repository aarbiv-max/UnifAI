"""
Helper functions for Slack event processing.

This module contains utility functions that can be reused across different Slack event handlers.
"""
import time
from typing import Dict, Any


def resolve_event_time(payload: Dict[str, Any]) -> float:
    """
    Resolve the best-available event timestamp from a Slack event payload.
    
    Prefers the nested event's "event_ts" if it can be parsed as a float, otherwise falls back to the top-level "event_time" and finally to the current time.
    
    Returns:
        The resolved event timestamp as a float.
    """
    e = payload.get("event") or {}
    event_ts = e.get("event_ts")
    if event_ts is not None:
        try:
            return float(event_ts)
        except Exception:
            pass
    return float(payload.get("event_time") or time.time())

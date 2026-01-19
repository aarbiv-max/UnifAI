"""
Domain models for Slack event processing.

This module contains dataclasses and models used across different Slack event handlers.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class BaseSlackEvent:
    """
    Minimal base for typed Slack events.
    """
    type: str
    event_ts: Optional[str]


@dataclass(frozen=True)
class ChannelCreatedEvent(BaseSlackEvent):
    """
    Typed model for Slack 'channel_created' event payload.
    """
    channel_id: str
    channel_name: str
    is_private: bool
    channel_raw: Dict[str, Any]

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "ChannelCreatedEvent":
        """
        Create a ChannelCreatedEvent by extracting event and channel fields from a Slack webhook payload.
        
        Parameters:
            payload (Dict[str, Any]): Raw Slack webhook payload containing an "event" object with an optional "channel" object.
        
        Returns:
            ChannelCreatedEvent: Instance populated from the payload; missing string fields default to empty strings and absent "is_private" is treated as False.
        """
        e = payload.get("event") or {}
        ch = e.get("channel") or {}
        return cls(
            type=e.get("type", ""),
            event_ts=e.get("event_ts"),
            channel_id=ch.get("id", ""),
            channel_name=ch.get("name", ""),
            is_private=bool(ch.get("is_private", False)),
            channel_raw=ch,
        )

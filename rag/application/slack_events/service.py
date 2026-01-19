"""
Application service to dispatch Slack events to their handlers.
"""
from typing import Dict, Any, Callable

from domain.slack_event.port import SlackEventHandler


class SlackEventService:
    """
    Maintains a registry of handler factories and dispatches payloads by event type.
    """
    
    def __init__(self):
        # Maps event_type -> factory that returns a SlackEventHandler
        """
        Initialize the SlackEventService.
        
        Sets up an empty registry that maps Slack event type strings to factory callables which produce SlackEventHandler instances.
        """
        self._event_factories: Dict[str, Callable[[], SlackEventHandler]] = {}
    
    def register_factory(self, event_type: str, factory: Callable[[], SlackEventHandler]) -> None:
        """Register a factory function that creates a handler for the given event type."""
        self._event_factories[event_type] = factory
    
    def dispatch(self, payload: Dict[str, Any]) -> bool:
        """
        Dispatches the given Slack event payload to a registered handler based on the payload's event type.
        
        Parameters:
            payload (Dict[str, Any]): Slack event payload expected to contain an "event" object with a "type" field.
        
        Returns:
            bool: True if a matching handler was found and invoked, False otherwise.
        """
        event_data = payload.get("event", {}) or {}
        event_type = event_data.get("type")
        if not event_type:
            return False
        
        event_factory = self._event_factories.get(event_type)
        if not event_factory:
            return False
        
        event_handler = event_factory()
        event_handler.handle(payload)
        return True

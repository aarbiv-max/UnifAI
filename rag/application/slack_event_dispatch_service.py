"""Slack event dispatch service - handles Slack Events API webhooks."""
from dataclasses import dataclass
from typing import Dict, Any, Optional

from domain.slack_event.dispatcher import SlackEventDispatcher, SlackEventTaskResult
from shared.logger import logger


@dataclass
class SlackEventResponse:
    """Response for Slack event handling."""
    success: bool
    event_type: str
    message: str
    task_result: Optional[SlackEventTaskResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the SlackEventResponse into a dictionary suitable for JSON responses.
        
        The resulting dictionary always contains the keys "success", "event_type", and "message". If a `task_result` is present, the dictionary also includes a "task" key whose value is the serialized task result.
        
        Returns:
            Dict[str, Any]: A mapping with keys:
                - "success": whether handling succeeded
                - "event_type": the Slack event type
                - "message": a human-readable message
                - "task" (optional): serialized task result when available
        """
        result = {
            "success": self.success,
            "event_type": self.event_type,
            "message": self.message,
        }
        if self.task_result:
            result["task"] = self.task_result.to_dict()
        return result


class SlackEventDispatchService:
    """
    Application service for handling Slack Events API webhooks.
    
    Responsibilities:
    - Handle URL verification (Slack health check)
    - Dispatch event_callback payloads to async workers
    
    The service depends on the SlackEventDispatcher PORT, not on Celery directly,
    following Hexagonal Architecture principles.
    """

    def __init__(self, dispatcher: SlackEventDispatcher):
        """
        Create a service that dispatches Slack event payloads using the provided dispatcher.
        
        Parameters:
            dispatcher (SlackEventDispatcher): Port used to dispatch Slack event payloads for processing.
        """
        self._dispatcher = dispatcher

    def handle_webhook(self, payload: Dict[str, Any]) -> SlackEventResponse:
        """
        Process a Slack Events API webhook payload and return a normalized SlackEventResponse.
        
        Handles the following payload types:
        - `url_verification`: returns the Slack `challenge` value in the response message.
        - `event_callback`: dispatches the payload via the injected dispatcher; on success the response includes the dispatch `task_result`, on failure the response indicates the error.
        - any other type: treated as ignored and returns a success response indicating the event was ignored.
        
        Parameters:
            payload (Dict[str, Any]): Raw webhook payload received from Slack Events API.
        
        Returns:
            SlackEventResponse: Outcome of handling the webhook. For `url_verification`, `message` contains the challenge string. For successful `event_callback` dispatches, `task_result` contains the dispatcher result; on dispatch failure `success` is `False` and `message` contains the error. For unknown types, `message` states the event was ignored.
        """
        payload_type = payload.get("type", "unknown")

        # URL verification (Slack health check)
        if payload_type == "url_verification":
            challenge = payload.get("challenge", "")
            logger.info("Slack URL verification challenge received")
            return SlackEventResponse(
                success=True,
                event_type="url_verification",
                message=challenge,  # The challenge is returned in message for endpoint to use
            )

        # Event callback - dispatch to worker
        if payload_type == "event_callback":
            event_id = payload.get("event_id", "unknown")
            try:
                task_result = self._dispatcher.dispatch(payload)
                logger.info(f"Dispatched Slack event {event_id}")
                return SlackEventResponse(
                    success=True,
                    event_type="event_callback",
                    message="Event dispatched for processing",
                    task_result=task_result,
                )
            except Exception as e:
                logger.error(f"Failed to dispatch Slack event {event_id}: {e}")
                return SlackEventResponse(
                    success=False,
                    event_type="event_callback",
                    message=f"Failed to dispatch event: {e}",
                )

        # Unknown payload type
        logger.warning(f"Unknown Slack event type: {payload_type}")
        return SlackEventResponse(
            success=True,  # Still return 200 to Slack
            event_type=payload_type,
            message="Unknown event type, ignored",
        )

"""Handler for Slack 'channel_created' events."""
from typing import Dict, Any

from domain.slack_event.port import SlackEventHandler
from domain.slack_event.model import ChannelCreatedEvent
from domain.slack_channel.model import SlackChannel
from domain.slack_channel.repository import SlackChannelRepository
from shared.logger import logger


class ChannelCreatedEventHandler(SlackEventHandler):
    """
    Processes Slack 'channel_created' event to persist the channel.
    
    This handler receives webhook events when a new Slack channel is created
    and persists the channel information to the database.
    """
    
    event_type = "channel_created"
    
    def __init__(self, channel_repo: SlackChannelRepository, project_id: str):
        """
        Create a ChannelCreatedEventHandler bound to a channel repository and project.
        
        Parameters:
            channel_repo: Repository used to persist Slack channel entities.
            project_id: Project identifier to associate stored channels with.
        """
        self._channel_repo = channel_repo
        self._project_id = project_id
    
    def handle(self, payload: Dict[str, Any]) -> None:
        """
        Handle a Slack "channel_created" webhook payload and persist the resulting channel.
        
        Parses the incoming payload into a ChannelCreatedEvent, validates that it is a "channel_created" event with a channel identifier and payload, converts the Slack channel data into a SlackChannel domain model (using the handler's project_id), optionally overrides the channel's last_updated with the event timestamp, and saves the channel to the repository. Exceptions raised during processing are caught and not re-raised.
         
        Parameters:
            payload (Dict[str, Any]): Raw Slack webhook payload for the event.
        """
        try:
            typed = ChannelCreatedEvent.from_payload(payload)
            
            if typed.type != self.event_type:
                logger.debug(f"Ignoring event type '{typed.type}' in ChannelCreatedEventHandler")
                return
            
            if not typed.channel_id:
                logger.warning(f"Missing channel id for '{self.event_type}' event")
                return

            channel_info = typed.channel_raw
            if not channel_info:
                logger.warning(f"No channel payload found for {self.event_type}")
                return

            # Create domain model from Slack API response
            channel = SlackChannel.from_slack_api(channel_info, self._project_id)
            
            # Override last_updated with event timestamp if available
            if typed.event_ts:
                channel = SlackChannel(
                    channel_id=channel.channel_id,
                    channel_name=channel.channel_name,
                    project_id=channel.project_id,
                    channel_type=channel.channel_type,
                    is_private=channel.is_private,
                    is_app_member=channel.is_app_member,
                    last_updated=float(typed.event_ts),
                )

            created = self._channel_repo.save(channel)
            if created:
                logger.info(f"Cached new channel from {self.event_type}: {typed.channel_id}")
            else:
                logger.error(f"Failed to cache new channel from {self.event_type}: {typed.channel_id}")
                
        except Exception as e:
            logger.error(f"Error handling {self.event_type}: {e}", exc_info=True)

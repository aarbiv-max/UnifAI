"""SlackChannelService — channel-level operations for Slack data sources."""

from dataclasses import dataclass
from typing import List

from core.data_sources.service import DataSourceService
from core.data_sources.types.slack.domain.channel.repository import SlackChannelRepository
from core.data_sources.types.slack.domain.channel.restriction_checker import ChannelRestrictionChecker
from shared.logger import logger


@dataclass
class CleanupResult:
    """Outcome of a restricted-channel cleanup run."""
    removed_count: int
    removed_channels: List[str]


class SlackChannelService:
    """Orchestrates channel-level operations that span cache + embeddings."""

    def __init__(
        self,
        channel_repo: SlackChannelRepository,
        restriction_checker: ChannelRestrictionChecker,
        data_source_service: DataSourceService,
        project_id: str,
    ):
        self._channel_repo = channel_repo
        self._checker = restriction_checker
        self._ds_service = data_source_service
        self._project_id = project_id

    def cleanup_restricted_channels(self) -> CleanupResult:
        """
        Refresh restriction rules and remove channels that now match.

        For each restricted channel:
          1. Delete from the channel cache (MongoDB slack_channels)
          2. Delete the embedded data — source record, pipeline,
             and Qdrant vectors — via DataSourceService.delete()
        """
        self._checker.refresh()

        channels = self._channel_repo.find_all(self._project_id)
        removed: List[str] = []

        for ch in channels:
            if not self._checker.is_restricted(ch.channel_name):
                continue

            self._channel_repo.delete(ch.channel_id)

            result = self._ds_service.delete(ch.channel_id)
            if result.success:
                logger.info(
                    "Deleted embedded data for restricted channel '%s' "
                    "(vectors=%d)",
                    ch.channel_name,
                    result.vectors_deleted,
                )
            elif result.message:
                logger.warning(
                    "Channel '%s' cache removed but embedded data "
                    "deletion incomplete: %s",
                    ch.channel_name,
                    result.message,
                )

            removed.append(ch.channel_name)

        logger.info("Cleanup complete — removed %d restricted channels", len(removed))
        return CleanupResult(
            removed_count=len(removed),
            removed_channels=removed,
        )

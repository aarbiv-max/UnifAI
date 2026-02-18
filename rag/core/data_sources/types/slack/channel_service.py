"""SlackChannelService — channel-level operations for Slack data sources."""

from dataclasses import dataclass, field
from typing import List

from core.data_sources.service import DataSourceService
from core.data_sources.types.slack.domain.channel.repository import SlackChannelRepository
from core.data_sources.types.slack.domain.channel.restriction_checker import ChannelRestrictionChecker
from shared.logger import logger


@dataclass
class ReconcileResult:
    """Outcome of a restriction reconciliation run."""
    newly_restricted: List[str] = field(default_factory=list)
    newly_unrestricted: List[str] = field(default_factory=list)


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

    def reconcile_restrictions(self) -> ReconcileResult:
        """
        Refresh restriction rules and reconcile every channel's state.

        - Channels that are now restricted but weren't before:
            mark ``restricted=True`` and delete their embeddings.
        - Channels that are no longer restricted but were before:
            mark ``restricted=False`` so they reappear in the channel list
            (embeddings are NOT restored — re-ingestion is needed).
        """
        self._checker.refresh()

        channels = self._channel_repo.find_all(self._project_id)
        result = ReconcileResult()

        for ch in channels:
            should_restrict = self._checker.is_restricted(ch.channel_name)

            if should_restrict and not ch.restricted:
                self._channel_repo.set_restricted(ch.channel_id, True)
                self._delete_embeddings(ch.channel_id)
                result.newly_restricted.append(ch.channel_name)

            elif not should_restrict and ch.restricted:
                self._channel_repo.set_restricted(ch.channel_id, False)
                result.newly_unrestricted.append(ch.channel_name)

        logger.info(
            "Reconciliation complete — restricted %d, unrestricted %d",
            len(result.newly_restricted),
            len(result.newly_unrestricted),
        )
        return result

    def _delete_embeddings(self, channel_id: str) -> None:
        """Delete source record, pipeline, and Qdrant vectors for a channel."""
        if not self._ds_service.get_by_id(channel_id):
            return
        self._ds_service.delete(channel_id)
    
  
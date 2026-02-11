from typing import List, Optional, Dict, Any
from actions.common.base_action import BaseAction
from actions.common.action_models import BaseActionInput, BaseActionOutput, ActionType
from elements.providers.dataflow_client.config import DataflowProviderConfig
from elements.providers.dataflow_client.dataflow_provider_factory import DataflowProviderFactory
from elements.providers.dataflow_client.identifiers import Identifier as DataFlowProviderIdentifier
from elements.retrievers.slack.identifiers import Identifier as RetrieverIdentifier
from core.enums import ResourceCategory


class GetAvailableSlackChannelsInput(BaseActionInput):
    """Input for fetching available embedded Slack channels"""
    limit: int = 50
    cursor: Optional[str] = None
    search_regex: Optional[str] = None


class GetAvailableSlackChannelsOutput(BaseActionOutput):
    """Output for available Slack channels"""
    channels: List[Dict[str, Any]] = []
    next_cursor: Optional[str] = None
    has_more: bool = False
    total: int = 0


class GetAvailableSlackChannelsAction(BaseAction):
    """
    Fetches available embedded Slack channels from Dataflow service (sync).
    """

    uid = "dataflow.get_available_slack_channels"
    name = "get_available_slack_channels"
    description = "Retrieve available embedded Slack channels from the Dataflow service"
    action_type = ActionType.DISCOVERY
    input_schema = GetAvailableSlackChannelsInput
    output_schema = GetAvailableSlackChannelsOutput
    version = "1.0.0"
    tags = {"dataflow", "discovery", "slack", "channels"}
    elements = {(ResourceCategory.PROVIDER.value, DataFlowProviderIdentifier.TYPE),
                (ResourceCategory.RETRIEVER.value, RetrieverIdentifier.TYPE)}

    def execute(
            self,
            input_data: GetAvailableSlackChannelsInput,
            context: Optional[Dict[str, Any]] = None
    ) -> GetAvailableSlackChannelsOutput:
        """Execute Slack channels discovery (sync)."""
        try:
            config = DataflowProviderConfig()
            factory = DataflowProviderFactory()
            provider = factory.create(config)

            response = provider.get_available_slack_channels(
                limit=input_data.limit,
                cursor=input_data.cursor,
                search_regex=input_data.search_regex,
            )

            return GetAvailableSlackChannelsOutput(
                success=True,
                message=f"Found {response.total} channels",
                channels=[ch.model_dump() for ch in response.channels],
                next_cursor=response.nextCursor,
                has_more=response.hasMore,
                total=response.total
            )

        except Exception as e:
            return GetAvailableSlackChannelsOutput(
                success=False,
                message=f"Failed to retrieve Slack channels: {str(e)}",
                channels=[],
                total=0
            )

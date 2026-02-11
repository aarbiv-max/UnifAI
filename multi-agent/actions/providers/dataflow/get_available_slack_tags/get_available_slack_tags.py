from typing import List, Optional, Dict, Any
from actions.common.base_action import BaseAction
from actions.common.action_models import BaseActionInput, BaseActionOutput, ActionType
from elements.providers.dataflow_client.config import DataflowProviderConfig
from elements.providers.dataflow_client.dataflow_provider_factory import DataflowProviderFactory
from elements.providers.dataflow_client.identifiers import Identifier as DataFlowProviderIdentifier
from elements.retrievers.slack.identifiers import Identifier as RetrieverIdentifier
from core.enums import ResourceCategory


class GetAvailableSlackTagsInput(BaseActionInput):
    """Input for fetching available Slack tags"""
    limit: int = 50
    cursor: Optional[str] = None
    search_regex: Optional[str] = None


class GetAvailableSlackTagsOutput(BaseActionOutput):
    """Output for available Slack tags"""
    tags: List[str] = []
    next_cursor: Optional[str] = None
    has_more: bool = False
    total: int = 0


class GetAvailableSlackTagsAction(BaseAction):
    """
    Fetches available tags from Slack sources via Dataflow service (sync).
    """

    uid = "dataflow.get_available_slack_tags"
    name = "get_available_slack_tags"
    description = "Retrieve available tags from Slack sources via the Dataflow service"
    action_type = ActionType.DISCOVERY
    input_schema = GetAvailableSlackTagsInput
    output_schema = GetAvailableSlackTagsOutput
    version = "1.0.0"
    tags = {"dataflow", "discovery", "slack", "tags"}
    elements = {(ResourceCategory.PROVIDER.value, DataFlowProviderIdentifier.TYPE),
                (ResourceCategory.RETRIEVER.value, RetrieverIdentifier.TYPE)}

    def execute(
            self,
            input_data: GetAvailableSlackTagsInput,
            context: Optional[Dict[str, Any]] = None
    ) -> GetAvailableSlackTagsOutput:
        """Execute Slack tags discovery (sync)."""
        try:
            config = DataflowProviderConfig()
            factory = DataflowProviderFactory()
            provider = factory.create(config)

            response = provider.get_available_slack_tags(
                limit=input_data.limit,
                cursor=input_data.cursor,
                search_regex=input_data.search_regex,
            )

            return GetAvailableSlackTagsOutput(
                success=True,
                message=f"Found {response.total} tags",
                tags=[t.label for t in response.options],
                next_cursor=response.nextCursor,
                has_more=response.hasMore,
                total=response.total
            )

        except Exception as e:
            return GetAvailableSlackTagsOutput(
                success=False,
                message=f"Failed to retrieve Slack tags: {str(e)}",
                tags=[],
                total=0
            )

from typing import Dict, List, Literal, Optional
from .identifiers import Identifier
from pydantic import Field, HttpUrl
from elements.retrievers.common.base_config import BaseRetrieverConfig
from core.field_hints import ActionHint, HintType, HiddenHint, SelectionType


class SlackRetrieverConfig(BaseRetrieverConfig):
    """
    Retrieves messages from Slack via an API endpoint.
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE
    api_url: HttpUrl = Field(
        HttpUrl("http://unifai-dataflow-server:13456/api/slack/query.match"),
        # default_factory=lambda: HttpUrl(
            # "https://unifai-dataflow-server-tag-ai--pipeline.apps.stc-ai-e1-pp.imap.p1.openshiftapps.com/api/slack/query.match"),
        description="URL for retrieving slack messages from the API",
        json_schema_extra=HiddenHint(reason="UI hint to hide this value").to_hints()
    )
    top_k_results: int = Field(
        3, ge=1,
        description="Number of top Slack messages to return"
    )
    threshold: float = Field(
        0.3, ge=0.0, le=1.0,
        description="Minimum relevance score to include a message"
    )

    channels: Optional[List[Dict]] = Field(
        default=None,
        description="Filter results to specific Slack channels",
        json_schema_extra=ActionHint(
            action_uid="dataflow.get_available_slack_channels",
            display_name="channels",
            hint_type=HintType.POPULATE,
            selection_type=SelectionType.MANUAL,
            field_mapping="channels",
            display_field="name",
            multi_select=True,
            pagination=True,
            search=True,
        ).to_hints()
    )

    tags: Optional[List[str]] = Field(
        default=None,
        description="Filter results by tags",
        json_schema_extra=ActionHint(
            action_uid="dataflow.get_available_slack_tags",
            hint_type=HintType.POPULATE,
            selection_type=SelectionType.MANUAL,
            field_mapping="tags",
            multi_select=True,
            pagination=True,
            search=True,
        ).to_hints()
    )

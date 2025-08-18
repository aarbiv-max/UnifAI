from typing import Literal
from .identifiers import Identifier
from pydantic import Field, HttpUrl
from elements.retrievers.common.base_config import BaseRetrieverConfig


class SlackRetrieverConfig(BaseRetrieverConfig):
    """
    Retrieves messages from Slack via an API endpoint.
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE
    api_url: HttpUrl = Field(
        default_factory=lambda: HttpUrl("http://0.0.0.0:13456/api/slack/query.match"),
        description="URL for retrieving slack messages from the API"
    )
    top_k_results: int = Field(
        3, ge=1,
        description="Number of top Slack messages to return"
    )
    threshold: float = Field(
        0.3, ge=0.0, le=1.0,
        description="Minimum relevance score to include a message"
    )

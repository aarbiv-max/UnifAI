from typing import Literal,ClassVar
from .identifiers import Identifier
from pydantic import Field, HttpUrl
from elements.retrievers.common.base_config import BaseRetrieverConfig
from core.field_hints import HiddenHint
from config.app_config import AppConfig

class DocsRetrieverConfig(BaseRetrieverConfig):
    """
    Retrieves document passages via an API endpoint.
    """
    app_config: ClassVar[AppConfig] = AppConfig.get_instance()
    type: Literal[Identifier.TYPE] = Identifier.TYPE
    api_url: HttpUrl = Field(
        #HttpUrl("https://unifai-dataflow-server-tag-ai--pipeline.apps.stc-ai-e1-pp.imap.p1.openshiftapps.com/api/docs/query.match"),
        # default_factory=lambda: HttpUrl("https://unifai-dataflow-server-tag-ai--pipeline.apps.stc-ai-e1-pp.imap.p1.openshiftapps.com/api/docs/query.match"),
        #HttpUrl("http://unifai-dataflow-server:13456/api/docs/query.match"),
        HttpUrl(f"{app_config.dataflow_url}/api/docs/query.match"),
        description="URL for retrieving docs from the API",
        json_schema_extra=HiddenHint(reason="UI hint to hide this value").to_hints()
    )
    top_k_results: int = Field(
        3, ge=1,
        description="Number of top document passages to return"
    )
    threshold: float = Field(
        0.3, ge=0.0, le=1.0,
        description="Minimum relevance score to include a passage"
    )

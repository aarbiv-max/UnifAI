from typing import Any
from elements.common.base_factory import BaseFactory
from elements.common.exceptions import PluginConfigurationError
from .config import DocsRetrieverConfig
from .docs_retriever import DocsRetriever
from .identifiers import Identifier


class DocsRetrieverFactory(BaseFactory[DocsRetrieverConfig, DocsRetriever]):
    def accepts(self, cfg: DocsRetrieverConfig, element_type: str) -> bool:
        return element_type == Identifier.TYPE

    def create(self, cfg: DocsRetrieverConfig, **kwargs: Any) -> DocsRetriever:
        try:
            return DocsRetriever(api_url=cfg.api_url,
                                 top_k_results=cfg.top_k_results,
                                 threshold=cfg.threshold)
        except Exception as e:
            raise PluginConfigurationError(
                f"DocsRetrieverFactory.create() failed: {e}", cfg.dict()
            ) from e

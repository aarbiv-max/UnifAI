from typing import List, Optional, Union
from elements.retrievers.common.base_retriever import BaseRetriever
from elements.providers.dataflow_client.config import DataflowProviderConfig
from elements.providers.dataflow_client.dataflow_provider_factory import DataflowProviderFactory
from core.context import get_current_context


class DocsDataflowRetriever(BaseRetriever):
    """
    Retrieves document passages via Dataflow vector database.
    """

    @staticmethod
    def _extract_values(items: Optional[List[Union[dict, str]]], value_field: str) -> Optional[List[str]]:
        """
        Extract values from a list of items.
        Items can be dicts (with value stored in value_field) or plain strings.
        """
        if not items:
            return None
        
        result = []
        for item in items:
            if isinstance(item, dict):
                # Extract value from dict using the value_field key
                value = item.get(value_field) or item.get('value')
                if value:
                    result.append(str(value))
            elif isinstance(item, str):
                # Plain string - use as is
                result.append(item)
        
        return result if result else None

    def __init__(
            self,
            top_k_results: int,
            threshold: float,
            timeout: float = 30.0,
            doc_ids: Optional[List[Union[dict, str]]] = None,
            tags: Optional[List[str]] = None,
    ):
        self.threshold = threshold
        self.doc_ids = self._extract_values(doc_ids, 'id')
        self.tags = tags
        config = DataflowProviderConfig(
            top_k=top_k_results,
            timeout=timeout,
        )
        factory = DataflowProviderFactory()
        self._provider = factory.create(config)

    def retrieve(self, query: str) -> List[dict]:
        context = get_current_context()

        response = self._provider.query(
            query=query,
            scope=context.scope,
            logged_in_user=context.logged_in_user,
            doc_ids=self.doc_ids,
            tags=self.tags,
        )

        return [
            match.model_dump()
            for match in response.matches
            if match.score >= self.threshold
        ]

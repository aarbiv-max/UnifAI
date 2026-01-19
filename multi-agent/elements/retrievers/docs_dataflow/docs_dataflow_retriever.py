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
        Normalize a list of dicts or strings into a list of string values.
        
        If `items` is falsy, returns None. For each dict in `items`, extracts the value at `value_field` or, if absent, the `'value'` key and converts it to a string when present. Plain strings are included as-is. Returns None if no values are extracted.
        
        Parameters:
            items (Optional[List[Union[dict, str]]]): Collection of dicts or strings to normalize.
            value_field (str): Primary key name to read from dict items.
        
        Returns:
            Optional[List[str]]: List of extracted string values, or `None` when input is falsy or yields no values.
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
        """
            Initialize the retriever with Dataflow provider configuration and normalized document filters.
            
            Parameters:
                top_k_results (int): Maximum number of nearest neighbors to request from the provider.
                threshold (float): Minimum score threshold for returned matches.
                timeout (float): Provider request timeout in seconds.
                doc_ids (Optional[List[Union[dict, str]]]): Optional list of document identifiers or dicts containing an identifier under the key `'id'` (or `'value'`); normalized to a list of strings via `_extract_values` and stored on the instance, or `None` if not provided or empty.
                tags (Optional[List[str]]): Optional list of tags used to filter provider queries.
            
            """
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
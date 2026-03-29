from typing import List, Optional, Any


class RetrieverCapable:
    retriever: Optional[Any] = None

    def retrieve(self, query: str) -> List[str]:
        if self.retriever is None:
            return []
        return self.retriever.retrieve(query)
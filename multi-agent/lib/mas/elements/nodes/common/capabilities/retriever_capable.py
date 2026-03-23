from typing import Any, List
from mas.elements.llms.common.chat.message import ChatMessage


class RetrieverCapableMixin:
    """Adds document retrieval from one or more retrievers."""

    def __init__(self, *, retrievers: List[Any] = None, **kwargs: Any):
        super().__init__(**kwargs)  # MRO
        self.retrievers = retrievers or []

    def _retrieve(self, query: str) -> str:
        if not self.retrievers:
            return ""
        results = []
        for retriever in self.retrievers:
            result = retriever.retrieve(query)
            if result:
                results.append(result)
        return "\n\n".join(results)

    def augment_with_context(self, user_message: ChatMessage) -> ChatMessage:
        """
        If retrievers are available, retrieves context for the user message's content
        and returns a new ChatMessage with the context prepended.
        If no retrievers or no content, returns the original message.
        If no context is found, returns the original message.
        """
        if not self.retrievers or not user_message.content:
            return user_message

        prompt = user_message.content
        ctx = self._retrieve(prompt)

        if not ctx:
            return user_message

        return ChatMessage(
            role=user_message.role,
            content=f"context: {ctx}\nuser:\n{prompt}"
        )

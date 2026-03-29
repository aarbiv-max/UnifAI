from typing import Optional

from lib.utils.tool_utils import ToolRegistry


class RetrieverCapable:
    retriever: Optional[str]

    def create_retriever_tool(self, tool_registry: ToolRegistry):
        if self.retriever:
            return tool_registry.get_tool(self.retriever)
        return None
from typing import Optional

from lib.mas.elements.nodes.abstract_agent.abstract_agent import AbstractAgent
from lib.utils.tool_utils import ToolRegistry


class CustomAgent(AbstractAgent):
    retriever: Optional[str]

    def _create_builtin_tools(self, tool_registry: ToolRegistry) -> list:
        tools = super()._create_builtin_tools(tool_registry)
        if self.retriever:
            retriever_tool = tool_registry.get_tool(self.retriever)
            if retriever_tool:
                tools.append(retriever_tool)
        return tools
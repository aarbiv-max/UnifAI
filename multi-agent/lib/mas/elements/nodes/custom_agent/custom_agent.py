from typing import List

from multi_agent.lib.mas.elements.nodes.custom_agent.config import CustomAgentNodeConfig
from multi_agent.lib.mas.elements.nodes.agent_node import AgentNode
from multi_agent.lib.toolkit.tool import Tool
from multi_agent.lib.toolkit.retriever_tool import RetrieverTool


class CustomAgent(AgentNode):
    config: CustomAgentNodeConfig

    @property
    def retriever(self):
        return self.config.retriever

    def _create_builtin_tools(self) -> List[Tool]:
        tools = super()._create_builtin_tools()

        if self.retriever:
            tools.append(RetrieverTool(self.retriever))

        return tools
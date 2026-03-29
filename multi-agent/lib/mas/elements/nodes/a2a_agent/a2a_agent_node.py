from typing import List

from multi_agent.lib.mas.elements.nodes.a2a_agent.config import A2AAgentNodeConfig
from multi_agent.lib.mas.elements.nodes.agent_node import AgentNode
from multi_agent.lib.toolkit.tool import Tool
from multi_agent.lib.toolkit.retriever_tool import RetrieverTool


class A2AAgentNode(AgentNode):
    config: A2AAgentNodeConfig

    def __init__(self, id, node_config, template_id=None, summary=None, retriever=None):
        super().__init__(id, node_config, template_id, summary)
        self.retriever = retriever

    @property
    def retriever(self):
        return self.config.retriever

    def _create_builtin_tools(self) -> List[Tool]:
        tools = super()._create_builtin_tools()
        if self.retriever:
            tools.append(RetrieverTool(self.retriever))
        return tools

    def augment_with_context(self, context: str) -> str:
        if self.retriever:
            retrieved_context = self.retriever.retrieve(context)
            if retrieved_context:
                context = f"{context}\n\nContext:\n{retrieved_context}"
        return context
from typing import Optional

from lib.mas.elements.nodes.custom_agent.config import CustomAgentConfig
from lib.mas.elements.nodes.custom_agent.custom_agent_node import CustomAgentNode
from lib.mas.elements.nodes.custom_agent.validator import CustomAgentValidator
from lib.mas.elements.node_factory import NodeFactory


class CustomAgentNodeFactory(NodeFactory):
    @staticmethod
    def create_node(
        id: str,
        model_name: str,
        prompt_template: str,
        retriever: Optional[str],
        tools: list[str],
        **kwargs,
    ) -> CustomAgentNode:
        node = CustomAgentNode(
            id=id,
            model_name=model_name,
            prompt_template=prompt_template,
            retriever=retriever,
            tools=tools,
            **kwargs,
        )
        return node

    @staticmethod
    def create_config(
        model_name: str,
        prompt_template: str,
        retriever: Optional[str],
        tools: list[str],
    ) -> CustomAgentConfig:
        return CustomAgentConfig(
            model_name=model_name,
            prompt_template=prompt_template,
            retriever=retriever,
            tools=tools,
        )

    @staticmethod
    def create_validator():
        return CustomAgentValidator
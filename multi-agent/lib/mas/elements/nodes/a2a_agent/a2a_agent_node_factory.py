from typing import Optional

from lib.mas.elements.nodes.a2a_agent.a2a_agent_node import A2AAgentNode
from lib.mas.elements.nodes.a2a_agent.config import A2AAgentConfig
from lib.mas.elements.nodes.a2a_agent.validator import A2AAgentValidator
from lib.mas.elements.node_factory import NodeFactory


class A2AAgentNodeFactory(NodeFactory):
    @staticmethod
    def create_node(
        id: str,
        model_name: str,
        prompt_template: str,
        retriever: Optional[str],
        number_of_conversations: int,
        **kwargs,
    ) -> A2AAgentNode:
        node = A2AAgentNode(
            id=id,
            model_name=model_name,
            prompt_template=prompt_template,
            retriever=retriever,
            number_of_conversations=number_of_conversations,
            **kwargs,
        )
        return node

    @staticmethod
    def create_config(
        model_name: str,
        prompt_template: str,
        retriever: Optional[str],
        number_of_conversations: int,
    ) -> A2AAgentConfig:
        return A2AAgentConfig(
            model_name=model_name,
            prompt_template=prompt_template,
            retriever=retriever,
            number_of_conversations=number_of_conversations,
        )

    @staticmethod
    def create_validator():
        return A2AAgentValidator
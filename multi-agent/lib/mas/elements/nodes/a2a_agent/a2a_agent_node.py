from typing import Optional

from lib.mas.elements.nodes.abstract_agent.abstract_agent_node import AbstractAgentNode


class A2AAgentNode(AbstractAgentNode):
    model_name: str
    prompt_template: str
    retriever: Optional[str]
    number_of_conversations: int

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_name = kwargs.get("model_name")
        self.prompt_template = kwargs.get("prompt_template")
        self.retriever = kwargs.get("retriever")
        self.number_of_conversations = kwargs.get("number_of_conversations")
from typing import List

from ..common.base_llm import BaseLLM
from ...tools.common.base_tool import BaseTool


class MockLLM(BaseLLM):
    def bind_tools(self, tools: List[BaseTool]) -> None:
        pass

    def chat(self, messages: list[dict], stream: bool = False) -> str:
        return "[MOCK RESPONSE] Hello! You said: " + messages[-1]["content"]

    def name(self) -> str:
        return "mock"

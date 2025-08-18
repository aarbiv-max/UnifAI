from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any, List
from elements.tools.common.base_tool import BaseTool
from .chat.message import ChatMessage


class BaseLLM(ABC):
    """
    Abstract base class for all LLM integrations (OpenAI, LlamaStack, etc.)
    """

    @abstractmethod
    def chat(self, messages: List[ChatMessage], stream: bool = False) -> ChatMessage:
        """
        Perform a conversational completion.
        messages = list of {"role": "user"/"assistant", "content": "..."}
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """
        Returns the identifier for the LLM (for logging/debug).
        """
        pass

    @abstractmethod
    def bind_tools(self, tools: List[BaseTool]) -> None:
        """
        Bind tools to the LLM for use in completions.
        """
        pass

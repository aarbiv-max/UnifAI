from typing import Protocol, runtime_checkable, Mapping, Any, Iterator
from abc import ABC, abstractmethod
from .enums import ResourceCategory


@runtime_checkable
class SupportsStreaming(Protocol):
    def _stream(self, payload: Mapping[str, Any]) -> None: ...

    def is_streaming(self) -> bool: ...


class LLMSupportsStreaming(ABC):
    @abstractmethod
    def stream(self, messages: list[Any], **kwargs) -> Iterator[str]:
        """
        Yields each token (or chunk) as it arrives.
        """
        ...


class SessionRegistry(Protocol):
    def register(self, category: ResourceCategory, rid: str, 
                instance: Any, config: Any, spec: Any) -> None: ...

    def get(self, category: ResourceCategory, rid: str) -> Any: ...
    
    def get_instance(self, category: ResourceCategory, rid: str) -> Any: ...
    
    def get_config(self, category: ResourceCategory, rid: str) -> Any: ...
    
    def get_spec(self, category: ResourceCategory, rid: str) -> Any: ...

    def get_runtime_element(self, category: ResourceCategory, rid: str) -> Any: ...

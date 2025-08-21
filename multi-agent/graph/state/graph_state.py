from typing import Any, Dict, Iterator, List, Tuple, Set
from typing_extensions import Annotated
from pydantic import BaseModel, Field, ConfigDict
from elements.llms.common.chat.message import ChatMessage
from .merge_strategies import merge_string_dicts, append_chat_messages, merge_dynamic_fields, append_iem_packets, merge_task_threads, merge_threads, merge_workspaces
from enum import Enum


class GraphState(BaseModel):
    """
    Pydantic-backed execution state for LangGraph.

    • Declares your main channels with merge-strategies via Annotated
    • Allows arbitrary extra keys at runtime (extra="allow")
    • Behaves like a dict: __getitem__, __setitem__, keys(), items(), etc.
    • Properly handles state persistence across LangGraph nodes
    • Raises KeyError for non-existent keys (like standard dict)
    """
    model_config = ConfigDict(
        extra="allow",  # permit new keys on the fly
        arbitrary_types_allowed=True  # in case you store non‐JSON types
    )

    # —————– Channels (with merge strategies) —————–
    # last-writer-wins for user_prompt:
    user_prompt: Annotated[str, lambda old, new: new] = Field(default="", json_schema_extra={'external': True})
    # merge dicts into a new dict:
    nodes_output: Annotated[Dict[str, str], merge_string_dicts] = Field(default_factory=dict)

    # appending messages to a list:
    messages: Annotated[list[ChatMessage], append_chat_messages] = Field(default_factory=list)

    # last-writer-wins for output
    output: Annotated[str, lambda old, new: new] = ""

    target_branch: Annotated[str, lambda old, new: new] = ""

    # Dynamic storage for extra fields (will be included in serialization)
    dynamic_fields: Annotated[Dict[str, Any], merge_dynamic_fields] = Field(default_factory=dict)

    # —————– STRUCTURED COMMUNICATION (Inter-Node Coordination) —————–
    # IEM protocol packets for structured node-to-node communication
    inter_packets: Annotated[List[Any], append_iem_packets] = Field(default_factory=list)
    
    # —————– PRIVATE WORKSPACE (Node Internal State) —————–

    # Task-focused conversation threads (agentic context)
    # Structure: {thread_id: [ChatMessage, ...]}
    task_threads: Annotated[Dict[str, List[ChatMessage]], merge_task_threads] = Field(default_factory=dict)
    
    # —————– ENGENTIC WORKLOAD MANAGEMENT —————–
    # Thread metadata management (Thread objects)
    # Structure: {thread_id: Thread}
    threads: Annotated[Dict[str, Any], merge_threads] = Field(default_factory=dict)
    
    # Workspace shared context management (Workspace objects)  
    # Structure: {thread_id: Workspace}
    workspaces: Annotated[Dict[str, Any], merge_workspaces] = Field(default_factory=dict)

    # —————– Dict-like API —————–
    def __getitem__(self, key: str) -> Any:
        # 1) declared field?
        if key in self.__class__.model_fields:
            return getattr(self, key)
        # 2) dynamic field?
        if key in self.dynamic_fields:
            return self.dynamic_fields[key]
        # 3) not found anywhere - raise KeyError
        raise KeyError(f"{key!r} not found in state.")

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self.__class__.model_fields:
            setattr(self, key, value)
        else:
            # Store in dynamic_fields which is preserved during serialization
            self.dynamic_fields[key] = value

    def __delitem__(self, key: str) -> None:
        if key in self.__class__.model_fields:
            delattr(self, key)
        elif key in self.dynamic_fields:
            del self.dynamic_fields[key]
        else:
            raise KeyError(f"{key!r} not found in state.")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Safe dictionary-like get method that doesn't raise KeyError
        """
        if key in self.__class__.model_fields:
            return getattr(self, key)
        return self.dynamic_fields.get(key, default)

    def update(self, data: Dict[str, Any]) -> None:
        for k, v in data.items():
            self[k] = v

    def keys(self) -> Iterator[str]:
        return iter(list(self.__class__.model_fields.keys()) + list(self.dynamic_fields.keys()))

    @classmethod
    def get_external_channels(cls) -> Set[str]:
        """
        Returns names of all fields marked as external variables/channels
        """
        return set([field_name for field_name, field_info in cls.model_fields.items()
                    if field_info.json_schema_extra and field_info.json_schema_extra.get('external', False)])

    def items(self) -> Iterator[Tuple[str, Any]]:
        for k in self.__class__.model_fields:
            yield k, getattr(self, k)
        for k, v in self.dynamic_fields.items():
            yield k, v

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Override Pydantic's model_dump() to include both
        declared fields and dynamic extras.
        """
        base = super().model_dump(*args, **kwargs)
        # Remove dynamic_fields from base if present to avoid duplication
        if "dynamic_fields" in base:
            base.pop("dynamic_fields")
        return {**base, **self.dynamic_fields}

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Override Pydantic's model_dump() for compatibility
        """
        return self.dict(*args, **kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.dict()})"


def _build_channel_enum() -> Enum:
    mapping = {name.upper(): name for name in GraphState.model_fields}
    return Enum("Channel", mapping, type=str)


Channel = _build_channel_enum()

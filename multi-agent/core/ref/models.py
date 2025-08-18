from typing import ClassVar, Literal, Annotated, Optional
from pydantic import RootModel, model_serializer, SerializerFunctionWrapHandler, SerializationInfo, Field
from core.enums import ResourceCategory


class Ref(RootModel[str]):
    """
    A wrapper around a single string that may be:
      - a bare ID, e.g. "abcd-1234"
      - an external ref, e.g. "$ref:abcd-1234"

    Exposes:
      - .root         the original string
      - .ref          the ID without prefix
      - .is_external_ref()
      - .is_inline()
      - .get_category()  NEW: get resource category
    """
    REF_PREFIX: ClassVar[str] = "$ref:"
    _category: ClassVar[Optional[ResourceCategory]] = None

    @property
    def ref(self) -> str:
        raw = self.root
        if raw.startswith(self.REF_PREFIX):
            return raw[len(self.REF_PREFIX):]
        return raw

    def is_external_ref(self) -> bool:
        return self.root.startswith(self.REF_PREFIX)

    def is_inline(self) -> bool:
        return not self.is_external_ref()
    
    def get_category(self) -> Optional[ResourceCategory]:
        """Get the resource category this ref points to."""
        return getattr(self.__class__, '_category', None)

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler, info: SerializationInfo) -> str:
        """
        For 'json' output: return raw self.root (preserve $ref:)
        For 'python' output: return self.ref (strip $ref:)
        """
        if info.mode == "json":
            return self.root
        return self.ref


# Specific Ref classes with category information + JSON schema
class LLMRef(Ref):
    """Reference to an LLM resource."""
    _category: ClassVar[ResourceCategory] = ResourceCategory.LLM
    
    model_config = {
        "json_schema_extra": {
            "category": ResourceCategory.LLM.value,
            "description": "Reference to an LLM resource",
            "examples": ["$ref:gpt-4-turbo", "openai-gpt4"]
        }
    }


class NodeRef(Ref):
    """Reference to a Node resource."""
    _category: ClassVar[ResourceCategory] = ResourceCategory.NODE
    
    model_config = {
        "json_schema_extra": {
            "category": ResourceCategory.NODE.value,
            "description": "Reference to a Node resource", 
            "examples": ["$ref:custom-agent-1", "data-processor"]
        }
    }


class RetrieverRef(Ref):
    """Reference to a Retriever resource."""
    _category: ClassVar[ResourceCategory] = ResourceCategory.RETRIEVER
    
    model_config = {
        "json_schema_extra": {
            "category": ResourceCategory.RETRIEVER.value,
            "description": "Reference to a Retriever resource",
            "examples": ["$ref:docs-retriever", "slack-search"]
        }
    }


class ToolRef(Ref):
    """Reference to a Tool resource."""
    _category: ClassVar[ResourceCategory] = ResourceCategory.TOOL
    
    model_config = {
        "json_schema_extra": {
            "category": ResourceCategory.TOOL.value,
            "description": "Reference to a Tool resource",
            "examples": ["$ref:jira-tool", "slack-messenger"]
        }
    }


class ProviderRef(Ref):
    """Reference to a Provider resource."""
    _category: ClassVar[ResourceCategory] = ResourceCategory.PROVIDER
    
    model_config = {
        "json_schema_extra": {
            "category": ResourceCategory.PROVIDER.value,
            "description": "Reference to a Provider resource",
            "examples": ["$ref:mcp-server", "api-provider"]
        }
    }


class ConditionRef(Ref):
    """Reference to a Condition resource."""
    _category: ClassVar[ResourceCategory] = ResourceCategory.CONDITION
    
    model_config = {
        "json_schema_extra": {
            "category": ResourceCategory.CONDITION.value,
            "description": "Reference to a Condition resource",
            "examples": ["$ref:threshold-check", "route-condition"]
        }
    }

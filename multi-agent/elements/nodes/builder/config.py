from elements.nodes.common.base_config import NodeBaseConfig
from pydantic import Field
from typing import Literal
from .identifiers import Identifier
from core.ref.models import LLMRef
from core.field_hints import ApiHint, HintType, SelectionType


class BuilderNodeConfig(NodeBaseConfig):
    """
    Configuration for the Builder Agent Node.
    
    The builder node creates workflows based on user requests.
    It requires an LLM for reasoning and uses injected services
    to search resources, create agents, and validate blueprints.
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE
    
    llm: LLMRef = Field(
        description="LLM reference for the builder agent's reasoning",
        json_schema_extra=ApiHint(
            endpoint="/resources/resource.validate",
            method="POST",
            hint_type=HintType.VALIDATE,
            selection_type=SelectionType.AUTOMATIC,
            dependencies={"llm": "resourceId"},
            field_mapping="is_valid"
        ).to_hints()
    )
    
    system_message: str = Field(
        default="",
        description="Custom system prompt for the builder agent"
    )
    
    max_rounds: int = Field(
        default=20,
        description="Maximum number of LLM reasoning rounds per phase",
        ge=1,
        le=100
    )


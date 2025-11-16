from elements.nodes.common.base_config import NodeBaseConfig
from pydantic import Field
from typing import Optional, List, Literal
from .identifiers import Identifier
from core.ref.models import LLMRef, ToolRef


class OrchestratorNodeConfig(NodeBaseConfig):
    """
    Orchestrator node configuration.
    
    Orchestrator nodes coordinate work execution by:
    - Creating work plans from incoming tasks
    - Delegating work items to adjacent nodes
    - Monitoring responses and updating plan status
    - Synthesizing results when complete
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE
    llm: LLMRef = Field(description="LLM Ref UID to use for planning and coordination")
    tools: Optional[List[ToolRef]] = Field(
        default_factory=list, 
        description="Domain-specific tools (orchestration tools added automatically)"
    )
    system_message: str = Field(
        "", 
        description="Domain specialization message (e.g., 'I specialize in document analysis and Slack integration'). This is separate from orchestrator behavior which is built-in."
    )
    max_rounds: int = Field(
        100,
        description="Maximum planning/execution rounds per orchestration cycle"
    )


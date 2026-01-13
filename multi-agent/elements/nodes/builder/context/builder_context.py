"""
Builder context management for multi-phase workflow creation.

Manages the state across the 4 phases: Analyze, Search, Design, Validate.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pydantic import BaseModel

from ..identifiers import BuilderPhase

if TYPE_CHECKING:
    from ..protocols import (
        ResourcesServiceProtocol,
        BlueprintServiceProtocol,
        CatalogServiceProtocol,
        ValidationServiceProtocol,
    )


class AnalysisResult(BaseModel):
    """Result from Phase 1: Analyze Request."""
    user_request: str = ""
    intent: str = ""
    required_capabilities: List[str] = []
    needs_orchestrator: bool = False
    suggested_agent_count: int = 1
    raw_analysis: str = ""


class ResourceSearchResult(BaseModel):
    """Result from Phase 2: Search Resources."""
    llms: List[Dict[str, Any]] = []
    providers: List[Dict[str, Any]] = []
    existing_nodes: List[Dict[str, Any]] = []
    existing_orchestrators: List[Dict[str, Any]] = []  # Existing orchestrator nodes
    missing_capabilities: List[str] = []
    has_required_llm: bool = False


class DesignResult(BaseModel):
    """Result from Phase 3: Design Workflow."""
    blueprint_draft: Dict[str, Any] = {}
    created_agent_rids: List[str] = []
    workflow_summary: str = ""
    plan_description: str = ""
    saved_blueprint_id: str = ""  # Populated after save_blueprint is called
    agents_created: int = 0  # Number of new agents created
    agents_reused: int = 0   # Number of existing agents reused
    uses_orchestrator: bool = False  # Whether workflow uses orchestrator


class ValidationResult(BaseModel):
    """Result from Phase 4: Validate."""
    is_valid: bool = False
    validation_errors: List[Dict[str, Any]] = []
    validation_warnings: List[Dict[str, Any]] = []
    suggestions: List[str] = []


@dataclass
class BuilderState:
    """
    Complete state for the builder agent across all phases.
    
    Accumulates results from each phase and provides context
    for the next phase.
    """
    # Current phase
    current_phase: BuilderPhase = BuilderPhase.ANALYZE
    
    # User context
    user_id: str = ""
    thread_id: str = ""
    
    # Phase results
    analysis: Optional[AnalysisResult] = None
    search_result: Optional[ResourceSearchResult] = None
    design_result: Optional[DesignResult] = None
    validation_result: Optional[ValidationResult] = None
    
    def advance_phase(self) -> None:
        """Advance to the next phase."""
        phase_order = [
            BuilderPhase.ANALYZE,
            BuilderPhase.SEARCH,
            BuilderPhase.DESIGN,
            BuilderPhase.VALIDATE,
            BuilderPhase.COMPLETE,
        ]
        current_idx = phase_order.index(self.current_phase)
        if current_idx < len(phase_order) - 1:
            self.current_phase = phase_order[current_idx + 1]


class BuilderContext:
    """
    Context manager for the builder agent.
    
    Provides access to state and services needed by builder tools.
    Thread-safe access to builder state.
    """
    
    def __init__(
        self,
        user_id: str,
        thread_id: str,
        resources_service: Optional["ResourcesServiceProtocol"] = None,
        blueprint_service: Optional["BlueprintServiceProtocol"] = None,
        catalog_service: Optional["CatalogServiceProtocol"] = None,
        validation_service: Optional["ValidationServiceProtocol"] = None,
    ):
        self._state = BuilderState(
            user_id=user_id,
            thread_id=thread_id,
        )
        self._resources_service = resources_service
        self._blueprint_service = blueprint_service
        self._catalog_service = catalog_service
        self._validation_service = validation_service
    
    @property
    def state(self) -> BuilderState:
        """Get current builder state."""
        return self._state
    
    @property
    def user_id(self) -> str:
        """Get user ID."""
        return self._state.user_id
    
    @property
    def current_phase(self) -> BuilderPhase:
        """Get current phase."""
        return self._state.current_phase
    
    @property
    def resources_service(self) -> Optional["ResourcesServiceProtocol"]:
        """Get resources service."""
        return self._resources_service
    
    @property
    def blueprint_service(self) -> Optional["BlueprintServiceProtocol"]:
        """Get blueprint service."""
        return self._blueprint_service
    
    @property
    def catalog_service(self) -> Optional["CatalogServiceProtocol"]:
        """Get catalog service."""
        return self._catalog_service
    
    @property
    def validation_service(self) -> Optional["ValidationServiceProtocol"]:
        """Get validation service."""
        return self._validation_service
    
    def set_analysis_result(self, result: AnalysisResult) -> None:
        """Set analysis result and advance phase."""
        self._state.analysis = result
        self._state.advance_phase()
    
    def set_search_result(self, result: ResourceSearchResult) -> None:
        """Set search result and advance phase."""
        self._state.search_result = result
        self._state.advance_phase()
    
    def set_design_result(self, result: DesignResult) -> None:
        """Set design result and advance phase."""
        self._state.design_result = result
        self._state.advance_phase()
    
    def set_validation_result(self, result: ValidationResult) -> None:
        """Set validation result."""
        self._state.validation_result = result
        if result.is_valid:
            self._state.advance_phase()
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context for LLM prompting."""
        summary = {
            "current_phase": self._state.current_phase.value,
            "user_id": self._state.user_id,
        }
        
        if self._state.analysis:
            summary["analysis"] = self._state.analysis.model_dump()
        
        if self._state.search_result:
            summary["available_resources"] = {
                "llm_count": len(self._state.search_result.llms),
                "provider_count": len(self._state.search_result.providers),
                "existing_agent_count": len(self._state.search_result.existing_nodes),
                "missing_capabilities": self._state.search_result.missing_capabilities,
            }
        
        if self._state.design_result:
            summary["design"] = {
                "workflow_summary": self._state.design_result.workflow_summary,
                "created_agents": self._state.design_result.created_agent_rids,
            }
        
        if self._state.validation_result:
            summary["validation"] = {
                "is_valid": self._state.validation_result.is_valid,
                "error_count": len(self._state.validation_result.validation_errors),
                "warning_count": len(self._state.validation_result.validation_warnings),
            }
        
        return summary


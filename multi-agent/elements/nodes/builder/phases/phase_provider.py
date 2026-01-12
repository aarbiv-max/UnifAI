"""
Builder Phase Provider.

Provides phase-specific tools and prompts for the builder agent.
Uses the PhaseDefinition pattern from the common agent module.
"""

from typing import Callable, Dict, List, Optional

from elements.tools.common.base_tool import BaseTool
from elements.llms.common.chat.message import ChatMessage, Role
from elements.nodes.common.agent.phases.phase_definition import (
    PhaseDefinition,
    PhaseSystem,
)

from ..identifiers import BuilderPhase
from ..context import BuilderContext
from ..prompts import (
    ANALYZE_PHASE_GUIDANCE,
    SEARCH_PHASE_GUIDANCE,
    DESIGN_PHASE_GUIDANCE,
    VALIDATE_PHASE_GUIDANCE,
)


class BuilderPhaseProvider:
    """
    Provides phase-specific context and tools for the builder agent.
    
    Uses PhaseDefinition pattern for clean separation of phase configuration.
    Manages transitions between phases and provides focused prompts.
    """
    
    def __init__(
        self,
        get_context: Callable[[], BuilderContext],
        tools_by_phase: Optional[Dict[BuilderPhase, List[BaseTool]]] = None,
        iteration_limits: Optional[Dict[BuilderPhase, int]] = None,
    ):
        """
        Initialize the phase provider.
        
        Args:
            get_context: Callable to get current builder context
            tools_by_phase: Map of phase to available tools
            iteration_limits: Custom iteration limits per phase
        """
        self._get_context = get_context
        self._tools_by_phase = tools_by_phase or {}
        self._iteration_limits = iteration_limits or {}
        
        # Build the phase system
        self._phase_system = self._build_phase_system()
    
    def _build_phase_system(self) -> PhaseSystem:
        """Build the complete phase system with PhaseDefinition objects."""
        phase_system = PhaseSystem(
            name="builder",
            description="Multi-phase workflow builder agent"
        )
        
        # ANALYZE phase
        analyze_phase = PhaseDefinition(
            name=BuilderPhase.ANALYZE.value,
            description="Parse and understand the user's workflow requirements",
            tools=self._tools_by_phase.get(BuilderPhase.ANALYZE, []),
            guidance=ANALYZE_PHASE_GUIDANCE,
            max_iterations=self._iteration_limits.get(BuilderPhase.ANALYZE, 5),
        )
        phase_system.add_phase(analyze_phase)
        
        # SEARCH phase
        search_phase = PhaseDefinition(
            name=BuilderPhase.SEARCH.value,
            description="Find available LLMs, providers, and existing agents",
            tools=self._tools_by_phase.get(BuilderPhase.SEARCH, []),
            guidance=SEARCH_PHASE_GUIDANCE,
            max_iterations=self._iteration_limits.get(BuilderPhase.SEARCH, 3),
        )
        phase_system.add_phase(search_phase)
        
        # DESIGN phase
        design_phase = PhaseDefinition(
            name=BuilderPhase.DESIGN.value,
            description="Create agents and generate the workflow blueprint",
            tools=self._tools_by_phase.get(BuilderPhase.DESIGN, []),
            guidance=DESIGN_PHASE_GUIDANCE,
            max_iterations=self._iteration_limits.get(BuilderPhase.DESIGN, 5),
        )
        phase_system.add_phase(design_phase)
        
        # VALIDATE phase
        validate_phase = PhaseDefinition(
            name=BuilderPhase.VALIDATE.value,
            description="Validate the blueprint and present for approval",
            tools=self._tools_by_phase.get(BuilderPhase.VALIDATE, []),
            guidance=VALIDATE_PHASE_GUIDANCE,
            max_iterations=self._iteration_limits.get(BuilderPhase.VALIDATE, 5),
        )
        phase_system.add_phase(validate_phase)
        
        # COMPLETE phase (terminal)
        complete_phase = PhaseDefinition(
            name=BuilderPhase.COMPLETE.value,
            description="Workflow building is complete",
            tools=[],
            guidance="The workflow has been designed and validated. Present the final summary to the user.",
            max_iterations=1,
        )
        phase_system.add_phase(complete_phase)
        
        return phase_system
    
    @property
    def phase_system(self) -> PhaseSystem:
        """Get the phase system."""
        return self._phase_system
    
    def get_current_phase(self) -> BuilderPhase:
        """Get the current phase from context."""
        return self._get_context().current_phase
    
    def get_phase_definition(self, phase: Optional[BuilderPhase] = None) -> Optional[PhaseDefinition]:
        """Get PhaseDefinition for a phase."""
        phase = phase or self.get_current_phase()
        return self._phase_system.get_phase(phase.value)
    
    def get_phase_guidance(self, phase: Optional[BuilderPhase] = None) -> str:
        """Get guidance for a phase."""
        phase = phase or self.get_current_phase()
        return self._phase_system.get_guidance_for_phase(phase.value)
    
    def get_tools_for_phase(self, phase: Optional[BuilderPhase] = None) -> List[BaseTool]:
        """Get tools available for a phase."""
        phase = phase or self.get_current_phase()
        return self._phase_system.get_tools_for_phase(phase.value)
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all tools from all phases."""
        all_tools = []
        for phase_def in self._phase_system.phases:
            all_tools.extend(phase_def.tools)
        return all_tools
    
    def get_max_iterations(self, phase: Optional[BuilderPhase] = None) -> int:
        """Get max iterations for a phase."""
        phase_def = self.get_phase_definition(phase)
        return phase_def.max_iterations if phase_def else 10
    
    def get_next_phase(self, phase: Optional[BuilderPhase] = None) -> Optional[BuilderPhase]:
        """Get the next phase in the sequence."""
        phase = phase or self.get_current_phase()
        phase_order = [
            BuilderPhase.ANALYZE,
            BuilderPhase.SEARCH,
            BuilderPhase.DESIGN,
            BuilderPhase.VALIDATE,
            BuilderPhase.COMPLETE,
        ]
        try:
            idx = phase_order.index(phase)
            if idx < len(phase_order) - 1:
                return phase_order[idx + 1]
        except ValueError:
            pass
        return None
    
    def can_advance(self) -> bool:
        """Check if we can advance to the next phase."""
        context = self._get_context()
        phase = context.current_phase
        
        if phase == BuilderPhase.ANALYZE:
            return context.state.analysis is not None
        elif phase == BuilderPhase.SEARCH:
            search = context.state.search_result
            return search is not None and search.has_required_llm
        elif phase == BuilderPhase.DESIGN:
            return context.state.design_result is not None
        elif phase == BuilderPhase.VALIDATE:
            validation = context.state.validation_result
            return validation is not None and validation.is_valid
        elif phase == BuilderPhase.COMPLETE:
            return True
        
        return False
    
    def advance_phase(self) -> BuilderPhase:
        """Advance to the next phase."""
        context = self._get_context()
        context.state.advance_phase()
        return context.current_phase
    
    def get_context_messages(self) -> List[ChatMessage]:
        """
        Get context messages based on current phase and accumulated state.
        """
        context = self._get_context()
        messages = []
        
        # Add phase-specific context
        summary = context.get_context_summary()
        
        # Build context message
        context_msg = f"""## Current Context

**Phase**: {summary['current_phase']}
**User**: {summary['user_id']}
"""
        
        if 'analysis' in summary:
            analysis = summary['analysis']
            context_msg += f"""
**Analysis Results**:
- Intent: {analysis.get('intent', 'N/A')}
- Required Capabilities: {', '.join(analysis.get('required_capabilities', []))}
- Needs Orchestrator: {analysis.get('needs_orchestrator', False)}
"""
        
        if 'available_resources' in summary:
            resources = summary['available_resources']
            context_msg += f"""
**Available Resources**:
- LLMs: {resources.get('llm_count', 0)}
- Providers: {resources.get('provider_count', 0)}
- Existing Agents: {resources.get('existing_agent_count', 0)}
- Missing Capabilities: {', '.join(resources.get('missing_capabilities', []))}
"""
        
        if 'design' in summary:
            design = summary['design']
            context_msg += f"""
**Design**:
- Summary: {design.get('workflow_summary', 'N/A')}
- Created Agents: {', '.join(design.get('created_agents', []))}
"""
        
        if 'validation' in summary:
            validation = summary['validation']
            context_msg += f"""
**Validation**:
- Valid: {validation.get('is_valid', False)}
- Errors: {validation.get('error_count', 0)}
- Warnings: {validation.get('warning_count', 0)}
"""
        
        messages.append(ChatMessage(
            role=Role.SYSTEM,
            content=context_msg
        ))
        
        return messages

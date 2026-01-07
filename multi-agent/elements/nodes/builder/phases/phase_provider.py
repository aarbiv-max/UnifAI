"""
Builder Phase Provider.

Provides phase-specific tools and prompts for the builder agent.
Similar to OrchestratorPhaseProvider pattern.
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

from elements.tools.common.base_tool import BaseTool
from elements.llms.common.chat.message import ChatMessage, Role

from ..identifiers import BuilderPhase
from ..context import BuilderContext


@dataclass
class PhaseConfig:
    """Configuration for a builder phase."""
    name: str
    description: str
    prompt_template: str
    required_tools: List[str]
    next_phase: Optional[BuilderPhase] = None
    can_retry: bool = True


class BuilderPhaseProvider:
    """
    Provides phase-specific context and tools for the builder agent.
    
    Manages transitions between phases and provides focused prompts.
    """
    
    # Phase configurations
    PHASE_CONFIGS: Dict[BuilderPhase, PhaseConfig] = {
        BuilderPhase.ANALYZE: PhaseConfig(
            name="Analyze Request",
            description="Parse and understand the user's workflow requirements",
            prompt_template="""## Phase 1: Analyze Request

Your task is to analyze the user's request and extract:
1. The main intent/goal of the workflow
2. Required capabilities (e.g., "search Jira", "send email", "summarize documents")
3. Whether multiple agents are needed (if yes, an orchestrator will be required)
4. Suggested number of agents

User Request: {user_request}

Think through this carefully and identify:
- What actions need to be performed?
- What external systems/tools are mentioned?
- Does this require coordination between multiple specialists?

After analysis, use the search_resources tool to find available resources.""",
            required_tools=[],
            next_phase=BuilderPhase.SEARCH,
        ),
        BuilderPhase.SEARCH: PhaseConfig(
            name="Search Resources",
            description="Find available LLMs, providers, and existing agents",
            prompt_template="""## Phase 2: Search Resources

Based on the analysis, search for available resources in the user's account.

Required capabilities: {required_capabilities}
Needs orchestrator: {needs_orchestrator}

Use the search_resources tool to find:
1. LLMs (MANDATORY - workflow cannot work without at least one LLM)
2. Providers/MCPs that match the required capabilities
3. Existing agents that could be reused

After searching, proceed to design the workflow.""",
            required_tools=["search_resources"],
            next_phase=BuilderPhase.DESIGN,
        ),
        BuilderPhase.DESIGN: PhaseConfig(
            name="Design Workflow",
            description="Create agents and generate the workflow blueprint",
            prompt_template="""## Phase 3: Design Workflow

Available resources:
- LLMs: {llm_count} available
- Providers: {provider_count} available  
- Existing agents: {agent_count} available

Required capabilities: {required_capabilities}

Design the workflow:
1. If new agents are needed, use create_agent tool to create them
2. Use generate_blueprint tool to create the workflow structure
3. Follow the orchestrator pattern if multiple agents are needed

Remember:
- Every workflow needs user_question_node and final_answer_node
- Multiple agents require an orchestrator_node
- Each agent needs an LLM reference""",
            required_tools=["create_agent", "generate_blueprint"],
            next_phase=BuilderPhase.VALIDATE,
        ),
        BuilderPhase.VALIDATE: PhaseConfig(
            name="Validate",
            description="Validate the blueprint and present for approval",
            prompt_template="""## Phase 4: Validate

Workflow has been designed. Now:
1. Use validate_blueprint tool to check for errors
2. If validation passes, use preview_workflow tool to present to user
3. If validation fails, you may need to fix issues or go back to design

The user will then approve or request changes.""",
            required_tools=["validate_blueprint", "preview_workflow"],
            next_phase=BuilderPhase.COMPLETE,
        ),
        BuilderPhase.COMPLETE: PhaseConfig(
            name="Complete",
            description="Workflow building is complete",
            prompt_template="""## Complete

The workflow has been designed and validated. 
Present the final summary to the user for approval.""",
            required_tools=[],
            next_phase=None,
            can_retry=False,
        ),
    }
    
    def __init__(
        self,
        get_context: Callable[[], BuilderContext],
        tools_by_phase: Dict[BuilderPhase, List[BaseTool]] = None,
    ):
        """
        Initialize the phase provider.
        
        Args:
            get_context: Callable to get current builder context
            tools_by_phase: Map of phase to available tools
        """
        self._get_context = get_context
        self._tools_by_phase = tools_by_phase or {}
    
    def get_current_phase(self) -> BuilderPhase:
        """Get the current phase from context."""
        return self._get_context().current_phase
    
    def get_phase_config(self, phase: BuilderPhase = None) -> PhaseConfig:
        """Get configuration for a phase."""
        phase = phase or self.get_current_phase()
        return self.PHASE_CONFIGS[phase]
    
    def get_phase_prompt(self, **kwargs) -> str:
        """
        Get the prompt for the current phase.
        
        Args:
            **kwargs: Template variables for the prompt
            
        Returns:
            Formatted prompt string
        """
        config = self.get_phase_config()
        return config.prompt_template.format(**kwargs)
    
    def get_tools_for_phase(self, phase: BuilderPhase = None) -> List[BaseTool]:
        """Get tools available for a phase."""
        phase = phase or self.get_current_phase()
        return self._tools_by_phase.get(phase, [])
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all tools from all phases."""
        all_tools = []
        for phase_tools in self._tools_by_phase.values():
            all_tools.extend(phase_tools)
        return all_tools
    
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


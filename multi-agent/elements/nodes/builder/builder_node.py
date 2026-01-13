"""
Builder Agent Node Implementation.

A multi-phase agent that creates workflows based on user requests.
Works in 4 phases:
1. Analyze Request - Parse and understand user requirements
2. Search Resources - Find available LLMs, providers, and existing agents
3. Design Workflow - Generate blueprint with orchestrator pattern if needed
4. Validate - Validate the blueprint before presenting for approval

Follows the OrchestratorNode pattern with phase-based execution.
"""

from typing import Optional, Any, List, ClassVar, Dict
from graph.state.state_view import StateView
from elements.llms.common.chat.message import ChatMessage, Role
from elements.tools.common.base_tool import BaseTool
from elements.nodes.common.base_node import BaseNode
from elements.nodes.common.capabilities.iem_capable import IEMCapableMixin
from elements.nodes.common.capabilities.llm_capable import LlmCapableMixin
from elements.nodes.common.capabilities.agent_capable import AgentCapableMixin
from elements.nodes.common.capabilities.workload_capable import WorkloadCapableMixin
from elements.nodes.common.agent import AgentConfig
from elements.nodes.common.agent.execution import ExecutionMode
from elements.nodes.common.agent.constants import StrategyType
from elements.tools.common.execution.models import ExecutorConfig
from elements.nodes.common.workload import Task, AgentResult

from .context import BuilderContext
from .identifiers import BuilderPhase
from .phases import BuilderPhaseProvider
from .prompts import (
    build_system_message,
    build_analyze_prompt,
    build_search_prompt,
    build_design_prompt,
    build_validate_prompt,
)


class BuilderNode(
    WorkloadCapableMixin,
    IEMCapableMixin,
    AgentCapableMixin,
    LlmCapableMixin,
    BaseNode
):
    """
    Builder Agent Node that creates workflows based on user requirements.
    
    Uses a 4-phase approach:
    1. ANALYZE: Parse user request and extract requirements
    2. SEARCH: Find available resources (LLMs, providers, agents)
    3. DESIGN: Generate blueprint with appropriate structure
    4. VALIDATE: Validate and present for approval
    
    Follows SOLID principles and reuses existing node patterns.
    
    Services are accessed lazily from AppContainer singleton to avoid
    circular dependencies and keep the factory simple.
    """

    READS: ClassVar[set[str]] = set()
    WRITES: ClassVar[set[str]] = set()

    def __init__(
            self,
            *,
            llm: Any,
            resources_service: Any = None,
            blueprint_service: Any = None,
            catalog_service: Any = None,
            validation_service: Any = None,
            system_message: str = "",
            max_rounds: int = 20,
            **kwargs: Any
    ):
        """
        Initialize the builder node.
        
        Args:
            llm: Language model for reasoning
            resources_service: Service for searching user resources (optional, lazy loaded)
            blueprint_service: Service for saving blueprints (optional, lazy loaded)
            catalog_service: Service for element catalog (optional, lazy loaded)
            validation_service: Service for validation (optional, lazy loaded)
            system_message: Custom system message
            max_rounds: Maximum LLM rounds across all phases
            **kwargs: Additional arguments for parent classes
        """
        super().__init__(
            llm=llm,
            system_message=build_system_message(system_message),
            **kwargs
        )
        
        self.max_rounds = max_rounds
        self.custom_system_message = system_message
        
        # Services (injected or lazy-loaded from AppContainer)
        self._resources_service = resources_service
        self._blueprint_service = blueprint_service
        self._catalog_service = catalog_service
        self._validation_service = validation_service
        
        # Builder context (created per execution)
        self._builder_context: Optional[BuilderContext] = None
        
        # Phase provider (created per execution)
        self._phase_provider: Optional[BuilderPhaseProvider] = None
        
        # Phase tools (built lazily)
        self._phase_tools: Dict[BuilderPhase, List[BaseTool]] = {}

    def _get_app_container(self) -> Optional[Any]:
        """
        Lazily access the AppContainer singleton.
        
        This allows the builder node to access services without requiring
        them to be injected at construction time.
        """
        try:
            from core.app_container import AppContainer
            return AppContainer()
        except Exception:
            return None

    @property
    def resources_service(self) -> Any:
        """Get resources service, lazy loading from AppContainer if needed."""
        if self._resources_service is None:
            container = self._get_app_container()
            if container:
                self._resources_service = container.resources_service
        return self._resources_service

    @property
    def blueprint_service(self) -> Any:
        """Get blueprint service, lazy loading from AppContainer if needed."""
        if self._blueprint_service is None:
            container = self._get_app_container()
            if container:
                self._blueprint_service = container.blueprint_service
        return self._blueprint_service

    @property
    def catalog_service(self) -> Any:
        """Get catalog service, lazy loading from AppContainer if needed."""
        if self._catalog_service is None:
            container = self._get_app_container()
            if container:
                self._catalog_service = container.catalog_service
        return self._catalog_service

    @property
    def validation_service(self) -> Any:
        """Get validation service, lazy loading from AppContainer if needed."""
        if self._validation_service is None:
            container = self._get_app_container()
            if container:
                self._validation_service = container.validation_service
        return self._validation_service

    def run(self, state: StateView) -> StateView:
        """
        Main entry point - process incoming task and run builder phases.
        """
        # Process all incoming packets
        self.process_packets(state)
        return state

    def handle_task_packet(self, packet) -> None:
        """
        Handle incoming task packet.
        
        Initializes builder context and runs through phases.
        Ensures cleanup of per-execution state after completion.
        """
        task = None
        try:
            # Extract and mark task as processed
            task = packet.extract_task()
            task.mark_processed(self.uid)
            
            # Initialize builder context
            thread_id = task.thread_id or self._create_thread(task)
            user_id = self._extract_user_id(task)
            
            self._builder_context = BuilderContext(
                user_id=user_id,
                thread_id=thread_id,
                resources_service=self.resources_service,
                blueprint_service=self.blueprint_service,
                catalog_service=self.catalog_service,
                validation_service=self.validation_service,
            )
            
            # Record task in workspace
            if thread_id:
                self.workspaces.add_task(thread_id, task)
            
            # Build tools for all phases
            self._build_phase_tools()
            
            # Create phase provider for context management
            self._phase_provider = BuilderPhaseProvider(
                get_context=lambda: self._builder_context,
                tools_by_phase=self._phase_tools,
            )
            
            # Run the builder phases
            result = self._run_builder_phases(task.content)
            
            # Create agent result
            agent_result = AgentResult(
                content=result.get("output", ""),
                agent_id=self.uid,
                agent_name=self.display_name,
                success=result.get("success", False),
                error=result.get("error"),
                reasoning=result.get("reasoning", ""),
                execution_metadata=result.get("metadata", {}),
            )
            
            # Add result to workspace
            if thread_id:
                self.workspaces.add_result(thread_id, agent_result)
            
            # Route response
            self._route_response(task, agent_result, packet)
            
        except Exception as e:
            error_result = AgentResult(
                content=f"Error building workflow: {str(e)}",
                agent_id=self.uid,
                agent_name=self.display_name,
                success=False,
                error=str(e)
            )
            if task:
                self._route_response(task, error_result, packet)
        finally:
            # Cleanup per-execution state to prevent stale data on next execution
            self._builder_context = None
            self._phase_provider = None
            self._phase_tools = {}

    def _run_builder_phases(self, user_request: str) -> Dict[str, Any]:
        """
        Run through all builder phases sequentially.
        
        Each phase has its own prompt and tools. The agent must complete
        each phase before moving to the next.
        
        Phases:
        1. ANALYZE: Parse request and identify requirements (no tools, LLM reasoning)
        2. SEARCH: Find available resources (search_resources tool)
        3. DESIGN: Create agents and blueprint (create_agent, generate_blueprint tools)
        4. VALIDATE: Validate and preview (validate_blueprint, preview_workflow tools)
        
        Args:
            user_request: The user's workflow request
            
        Returns:
            Final result dictionary
        """
        context = self._builder_context
        
        # Conversation history accumulates across phases
        conversation_history: List[ChatMessage] = []
        
        # Phase execution results
        phase_results: Dict[str, Any] = {}
        final_result: Dict[str, Any] = {
            "output": "",
            "success": False,
            "error": None,
            "reasoning": "",
            "metadata": {"phases_completed": []}
        }
        
        # ===== PHASE 1: ANALYZE =====
        self._stream_phase_event("analyze", "started", "Understanding your request...")
        
        analyze_result = self._run_phase(
            phase=BuilderPhase.ANALYZE,
            user_request=user_request,
            conversation_history=conversation_history,
            phase_prompt=build_analyze_prompt(user_request),
        )
        
        if not analyze_result.get("success"):
            self._stream_phase_event("analyze", "failed", analyze_result.get('error', 'Unknown error'))
            final_result["error"] = f"Phase ANALYZE failed: {analyze_result.get('error')}"
            return final_result
        
        self._stream_phase_event("analyze", "complete", "Request analyzed")
        phase_results["analyze"] = analyze_result
        final_result["metadata"]["phases_completed"].append("analyze")
        
        # ===== PHASE 2: SEARCH =====
        self._stream_phase_event("search", "started", "Searching available resources...")
        
        # Get capabilities from analysis for search prompt
        search_capabilities = []
        if context.state.analysis:
            search_capabilities = context.state.analysis.required_capabilities
        
        search_result = self._run_phase(
            phase=BuilderPhase.SEARCH,
            user_request=user_request,
            conversation_history=conversation_history,
            phase_prompt=build_search_prompt(search_capabilities),
        )
        
        if not search_result.get("success"):
            self._stream_phase_event("search", "failed", search_result.get('error', 'Unknown error'))
            final_result["error"] = f"Phase SEARCH failed: {search_result.get('error')}"
            return final_result
        
        # Check if we have required LLM
        if context.state.search_result and not context.state.search_result.has_required_llm:
            self._stream_phase_event("search", "failed", "No LLM found")
            final_result["output"] = "Cannot create workflow: No LLM found in your account. Please add an LLM resource first."
            final_result["error"] = "No LLM available"
            return final_result
        
        self._stream_phase_event("search", "complete", "Resources found")
        phase_results["search"] = search_result
        final_result["metadata"]["phases_completed"].append("search")
        
        # ===== PHASE 3: DESIGN =====
        self._stream_phase_event("design", "started", "Designing workflow...")
        
        # Build design prompt with context from search results
        search = context.state.search_result
        analysis = context.state.analysis
        
        llm_info = "No LLM available"
        if search and search.llms:
            llm = search.llms[0]
            llm_info = f"LLM: {llm.get('name', 'Unknown')} (rid: {llm.get('rid')})"
        
        agent_info = "No existing agents"
        if search and search.existing_nodes:
            agent_names = [a.get('name', 'Unknown') for a in search.existing_nodes]
            agent_info = f"Existing Agents: {', '.join(agent_names)}"
        
        design_result = self._run_phase(
            phase=BuilderPhase.DESIGN,
            user_request=user_request,
            conversation_history=conversation_history,
            phase_prompt=build_design_prompt(
                llm_info=llm_info,
                provider_count=len(search.providers) if search else 0,
                agent_info=agent_info,
                needs_orchestrator=analysis.needs_orchestrator if analysis else False,
            ),
        )
        
        if not design_result.get("success"):
            self._stream_phase_event("design", "failed", design_result.get('error', 'Unknown error'))
            final_result["error"] = f"Phase DESIGN failed: {design_result.get('error')}"
            return final_result
        
        self._stream_phase_event("design", "complete", "Workflow designed")
        phase_results["design"] = design_result
        final_result["metadata"]["phases_completed"].append("design")
        
        # ===== PHASE 4: VALIDATE =====
        self._stream_phase_event("validate", "started", "Validating and saving...")
        
        validate_result = self._run_phase(
            phase=BuilderPhase.VALIDATE,
            user_request=user_request,
            conversation_history=conversation_history,
            phase_prompt=build_validate_prompt(),
        )
        
        if validate_result.get("success"):
            self._stream_phase_event("validate", "complete", "Workflow saved!")
        else:
            self._stream_phase_event("validate", "failed", validate_result.get('error', 'Validation failed'))
        
        phase_results["validate"] = validate_result
        final_result["metadata"]["phases_completed"].append("validate")
        
        # Build final result
        final_result["success"] = validate_result.get("success", False)
        final_result["output"] = validate_result.get("output", "")
        final_result["reasoning"] = self._build_phase_summary(phase_results)
        
        # Extract blueprint_id from context state (set by save_blueprint tool)
        if context.state.design_result:
            if context.state.design_result.saved_blueprint_id:
                final_result["metadata"]["blueprint_id"] = context.state.design_result.saved_blueprint_id
            if context.state.design_result.blueprint_draft:
                blueprint_name = context.state.design_result.blueprint_draft.get("name", "")
                if blueprint_name:
                    final_result["metadata"]["workflow_name"] = blueprint_name
            
            # Add agent stats from design result
            if context.state.design_result.agents_created is not None:
                final_result["metadata"]["agents_created"] = context.state.design_result.agents_created
            if context.state.design_result.agents_reused is not None:
                final_result["metadata"]["agents_reused"] = context.state.design_result.agents_reused
            if context.state.design_result.uses_orchestrator is not None:
                final_result["metadata"]["uses_orchestrator"] = context.state.design_result.uses_orchestrator
        
        
        return final_result

    def _run_phase(
        self,
        phase: BuilderPhase,
        user_request: str,
        conversation_history: List[ChatMessage],
        phase_prompt: str,
    ) -> Dict[str, Any]:
        """
        Execute a single phase with its specific tools and prompt.
        
        Args:
            phase: The phase to execute
            user_request: Original user request (for context)
            conversation_history: Accumulated conversation (modified in place)
            phase_prompt: The prompt for this phase
            
        Returns:
            Phase execution result
        """
        # Get tools for this phase (prefer phase provider if available)
        if self._phase_provider:
            phase_tools = self._phase_provider.get_tools_for_phase(phase)
        else:
            phase_tools = self._phase_tools.get(phase, [])
        
        # Build messages for this phase
        messages = list(conversation_history)  # Copy existing history
        
        # Add phase context from provider if available
        if self._phase_provider:
            context_messages = self._phase_provider.get_context_messages()
            messages.extend(context_messages)
        
        messages.append(ChatMessage(
            role=Role.USER,
            content=phase_prompt
        ))
        
        # Create strategy with phase-specific tools
        strategy = self.create_strategy(
            tools=phase_tools,
            strategy_type=StrategyType.REACT.value,
            system_message=build_system_message(self.custom_system_message),
            max_steps=self.max_rounds // 4  # Divide rounds across phases
        )
        
        # Configure execution
        config = AgentConfig(
            execution_mode=ExecutionMode.AUTO,
            executor_config=ExecutorConfig.create_balanced()
        )
        
        # Run agent for this phase
        result = self.run_agent(
            messages=messages,
            strategy=strategy,
            config=config
        )
        
        # Update conversation history with the exchange
        conversation_history.append(ChatMessage(
            role=Role.USER,
            content=phase_prompt
        ))
        if result.get("output"):
            conversation_history.append(ChatMessage(
                role=Role.ASSISTANT,
                content=str(result.get("output"))
            ))
        
        
        return result

    def _build_phase_summary(self, phase_results: Dict[str, Any]) -> str:
        """Build a summary of all phase executions."""
        summary_parts = []
        
        for phase_name, result in phase_results.items():
            status = "✓" if result.get("success") else "✗"
            summary_parts.append(f"{status} {phase_name.upper()}")
        
        return " → ".join(summary_parts)

    def _stream_phase_event(self, phase: str, status: str, message: str) -> None:
        """
        Emit a streaming event for builder phase progress.
        
        Args:
            phase: Phase name (analyze, search, design, validate)
            status: Status (started, complete, failed)
            message: Human-readable message
        """
        if self.is_streaming():
            self._stream({
                "type": "builder_phase",
                "phase": phase,
                "status": status,
                "message": message,
            })

    def _build_phase_tools(self) -> None:
        """Build tools for each phase."""
        # Import tools here to avoid circular imports
        from .tools import (
            AnalyzeRequestTool,
            SearchResourcesTool,
            GenerateBlueprintTool,
            ValidateBlueprintTool,
            PreviewWorkflowTool,
            SaveBlueprintTool,
        )
        
        # Phase 1: Analyze - Tool to record analysis results
        self._phase_tools[BuilderPhase.ANALYZE] = [
            AnalyzeRequestTool(
                get_context=lambda: self._builder_context,
            ),
        ]
        
        # Phase 2: Search
        self._phase_tools[BuilderPhase.SEARCH] = [
            SearchResourcesTool(
                get_context=lambda: self._builder_context,
            ),
        ]
        
        # Phase 3: Design - uses AgentBuilder helper internally for agent creation
        self._phase_tools[BuilderPhase.DESIGN] = [
            GenerateBlueprintTool(
                get_context=lambda: self._builder_context,
            ),
        ]
        
        # Phase 4: Validate & Save
        self._phase_tools[BuilderPhase.VALIDATE] = [
            ValidateBlueprintTool(
                get_context=lambda: self._builder_context,
            ),
            PreviewWorkflowTool(
                get_context=lambda: self._builder_context,
            ),
            SaveBlueprintTool(
                get_context=lambda: self._builder_context,
            ),
        ]

    def _create_thread(self, task: Task) -> str:
        """Create a new thread for the builder task."""
        thread = self.threads.create_root_thread(
            title="Workflow Builder",
            objective=task.content[:100],
            initiator=self.uid
        )
        return thread.thread_id

    def _extract_user_id(self, task: Task) -> str:
        """Extract user ID from RunContext, task, or use default."""
        # Try to get from RunContext (most reliable)
        try:
            from core.context import get_current_context
            ctx = get_current_context()
            if ctx and ctx.user_id:
                return ctx.user_id
        except Exception:
            pass
        
        # Try to get from task metadata
        if hasattr(task, 'metadata') and task.metadata:
            user_id = task.metadata.get('user_id')
            if user_id:
                return user_id
        
        # Try to get from thread context
        if task.thread_id:
            try:
                thread = self.threads.get_thread(task.thread_id)
                if thread and hasattr(thread, 'user_id'):
                    return thread.user_id
            except Exception:
                pass
        
        # Default
        return "admin"

    def _route_response(self, task: Task, agent_result: AgentResult, original_packet) -> None:
        """Route response based on task settings."""
        if not task.should_respond:
            # Normal broadcast
            forked_task = task.fork(
                content="Workflow build complete",
                processed_by=self.uid,
                result=agent_result
            )
            self.broadcast_task(forked_task)
        else:
            # Direct response
            response_task = Task.respond_success(
                original_task=task,
                result=agent_result,
                processed_by=self.uid
            )
            self.reply_task(original_packet, response_task)


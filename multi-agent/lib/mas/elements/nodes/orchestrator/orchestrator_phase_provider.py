"""
Orchestrator-specific phase provider implementation.

Uses clean Pydantic models and enums to define orchestrator phases professionally.
"""

import logging
from enum import Enum
from typing import List, Callable, Any, Optional
from mas.elements.tools.common.base_tool import BaseTool
from mas.elements.llms.common.chat.message import ChatMessage
from mas.elements.nodes.common.agent.phases.unified_phase_provider import PhaseProvider
from mas.elements.nodes.common.agent.phases.phase_definition import PhaseSystem, PhaseDefinition
from mas.elements.nodes.common.agent.phases.phase_protocols import PhaseState, create_phase_state
from mas.elements.nodes.common.agent.phases.models import PhaseValidationContext
from .phases.models import PhaseIterationLimits
from .phases.validators import (
    PlanningValidator, ExecutionValidator,
    MonitoringValidator, SynthesisValidator
)
from .context import OrchestratorContextBuilder
from .context.snapshot import IterationSnapshot
from .phases.phase_machine import PhaseMachine
from .phases.prompt_builder import PromptBuilder
from .phases.context_formatter import ContextFormatter

# Built-in orchestration tools
from mas.elements.tools.builtin.workplan.create_or_update import CreateOrUpdateWorkPlanTool
from mas.elements.tools.builtin.workplan.mark_status import MarkWorkItemStatusTool
from mas.elements.tools.builtin.workplan.record_execution import RecordLocalExecutionTool
from mas.elements.tools.builtin.delegation.delegate_task import DelegateTaskTool
from mas.elements.tools.builtin.topology.list_adjacent import ListAdjacentNodesTool
from mas.elements.tools.builtin.time import GetCurrentTimeTool

logger = logging.getLogger(__name__)


class OrchestratorPhase(Enum):
    """
    Orchestrator execution phases (4-phase model).

    PLANNING owns both plan creation AND delegation — no separate ALLOCATION
    phase. This saves one LLM roundtrip per cycle without sacrificing structure.
    """
    PLANNING = "planning"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    SYNTHESIS = "synthesis"

    @classmethod
    def get_execution_order(cls) -> List['OrchestratorPhase']:
        return [cls.PLANNING, cls.EXECUTION, cls.MONITORING, cls.SYNTHESIS]

    @classmethod
    def get_phase_names(cls) -> List[str]:
        return [phase.value for phase in cls.get_execution_order()]


class OrchestratorPhaseProvider(PhaseProvider):
    """
    Professional orchestrator phase provider using clean Pydantic models and enums.

    Defines orchestrator phases with proper separation of concerns:
    - Domain tools come from init parameter (orchestrator's capabilities)
    - Orchestration tools are built-in (work plan, delegation, etc.)
    - Phases are defined using enums (no hardcoding)
    - Iteration limits managed via Pydantic models in PhaseDefinition

    DESIGN NOTE:
    The phase provider receives already-filtered adjacent nodes from the orchestrator.
    It does NOT know about delegation policies - that's the orchestrator's responsibility.
    This ensures clean separation: orchestrator decides WHO is adjacent, provider uses it.
    """

    def __init__(
            self,
            domain_tools: List[BaseTool],
            get_adjacent_nodes: Callable[[], Any],
            send_task: Callable[..., Any],
            node_uid: str,
            thread_id: str,
            get_workload_service: Callable[[], Any],
            context_builder: Optional[OrchestratorContextBuilder] = None,
            iteration_limits: Optional[PhaseIterationLimits] = None
    ):
        """
        Initialize orchestrator phase provider.

        Args:
            domain_tools: Domain-specific tools that this orchestrator can use
            get_adjacent_nodes: Function to get adjacent nodes (already filtered by orchestrator)
            send_task: Function to send IEM tasks (dst_uid, task) -> packet_id
            node_uid: Node identifier
            thread_id: Current thread ID for context
            get_workload_service: Function to get workload service
            context_builder: OrchestratorContextBuilder for recording phase transitions (optional)
            iteration_limits: Custom iteration limits configuration (optional)

        Note:
            get_adjacent_nodes should return nodes that the orchestrator has already
            filtered according to its delegation policy. The provider doesn't apply
            any additional filtering - it trusts what the orchestrator gives it.
        """
        self._get_adjacent_nodes = get_adjacent_nodes
        self._send_task = send_task
        self._node_uid = node_uid
        self._thread_id = thread_id
        self._domain_tools = domain_tools
        self._get_workload_service = get_workload_service
        self._context_builder = context_builder

        # Configure iteration limits using Pydantic model
        self._iteration_limits = iteration_limits or PhaseIterationLimits()

        # Private: Cascade safety limit
        self._max_cascade_transitions = 10

        # Orchestrator context (set by orchestrator_node before each cycle)
        self._current_orch_context = None

        # Track current user request for focused prompts
        self._current_user_request: Optional[str] = None

        # Track whether current iteration is a phase entry (for tiered context)
        self._phase_changed: bool = True

        # Iteration snapshot cache (populated per think() cycle, avoids redundant loads)
        self._cached_snapshot: Optional[IterationSnapshot] = None

        # Plan modification tracking: captures the plan's updated_at at cycle
        # start so we can detect whether the LLM has modified it.
        self._plan_updated_at_cycle_start: Optional[str] = None

        # Composable sub-components (SRP)
        self._phase_machine = PhaseMachine(
            iteration_limits=self._iteration_limits,
            max_cascade_transitions=self._max_cascade_transitions,
        )
        self._prompt_builder = PromptBuilder()
        self._context_formatter = ContextFormatter(
            thread_id=self._thread_id,
            node_uid=self._node_uid,
            get_adjacent_nodes=self._get_adjacent_nodes,
        )

        super().__init__(domain_tools)  # This calls _create_phase_system()

    def _get_current_thread(self):
        """Get current thread for delegation context."""
        workload_service = self._get_workload_service()
        return workload_service.get_thread(self._thread_id)

    def set_orch_context(self, orch_context) -> None:
        """
        Set orchestration context for this cycle.

        Also captures the plan's current updated_at timestamp so
        _contextualize_status can detect whether the LLM has modified
        the plan since the cycle started.
        """
        self._current_orch_context = orch_context

        # Snapshot the plan timestamp at cycle start for modification tracking
        try:
            ws = self._get_workload_service().get_workspace_service()
            plan = ws.load_work_plan(self._thread_id, self._node_uid)
            self._plan_updated_at_cycle_start = plan.updated_at if plan else None
        except Exception:
            self._plan_updated_at_cycle_start = None

    def set_current_user_request(self, request: str) -> None:
        """Set the current user request for building focused prompts."""
        self._current_user_request = request

    def set_phase_changed(self, changed: bool) -> None:
        """Signal whether the current iteration is a phase entry (full context) or continuation (brief)."""
        self._phase_changed = changed

    def begin_iteration(self) -> None:
        """
        Begin a new LLM iteration. Captures a fresh snapshot of workspace state.

        Call this at the start of each strategy.think() cycle. All subsequent
        calls to get_phase_context, get_dynamic_context_messages,
        build_focused_prompt, and _build_validation_context will use this
        cached snapshot instead of loading data independently.
        """
        self._cached_snapshot = IterationSnapshot.capture(
            get_workload_service=self._get_workload_service,
            get_adjacent_nodes=self._get_adjacent_nodes,
            thread_id=self._thread_id,
            node_uid=self._node_uid,
        )

    def end_iteration(self) -> None:
        """
        Invalidate the cached snapshot after think() completes.

        Tools execute AFTER think() returns but BEFORE the next
        should_continue() check.  Without invalidation, can_finish_now()
        would evaluate against the stale pre-tool-execution snapshot and
        incorrectly allow another think() cycle (which cascades to the
        next phase and may cause redundant re-delegation).
        """
        self._cached_snapshot = None

    @property
    def _snapshot(self) -> IterationSnapshot:
        """
        Lazily return the current iteration snapshot.

        If begin_iteration() was not called, captures a fresh one on demand.
        """
        if self._cached_snapshot is None:
            self.begin_iteration()
        return self._cached_snapshot

    def _create_phase_system(self) -> PhaseSystem:
        """
        Create the orchestrator phase system.

        Tool separation:
        - Built-in tools: Initialize here (workplan, delegation, topology, etc.)
        - Domain tools: Already initialized, passed from constructor (execution tools)

        Adjacent Nodes:
        - Phase provider receives already-filtered adjacent nodes from orchestrator
        - No policy logic here - orchestrator has already applied its delegation policy
        - Provider simply uses the nodes it's given
        """
        # Clean SOLID dependencies
        get_tid = lambda: self._thread_id
        get_uid = lambda: self._node_uid

        # Get adjacent nodes (already filtered by orchestrator)
        adjacent_nodes = self._get_adjacent_nodes()

        create_plan_tool = CreateOrUpdateWorkPlanTool(
            get_thread_id=get_tid,
            get_owner_uid=get_uid,
            get_workload_service=self._get_workload_service
        )
        mark_status_tool = MarkWorkItemStatusTool(
            get_thread_id=get_tid,
            get_owner_uid=get_uid,
            get_workload_service=self._get_workload_service
        )
        record_execution_tool = RecordLocalExecutionTool(
            get_thread_id=get_tid,
            get_owner_uid=get_uid,
            get_workload_service=self._get_workload_service
        )
        # Note: SummarizeWorkPlanTool removed - work plan is now provided via dynamic context

        delegate_tool = DelegateTaskTool(
            send_task=self._send_task,
            get_owner_uid=get_uid,
            get_current_thread=lambda: self._get_current_thread(),
            get_thread_service=lambda: self._get_workload_service().get_thread_service(),
            get_workspace_service=lambda: self._get_workload_service().get_workspace_service(),
            check_adjacency=lambda uid: uid in adjacent_nodes
        )
        list_nodes_tool = ListAdjacentNodesTool(
            get_adjacent_nodes=self._get_adjacent_nodes
        )
        time_tool = GetCurrentTimeTool()

        # Create phase definitions
        domain_tools_list = list(self._domain_tools)

        planning_validator = PlanningValidator()
        execution_validator = ExecutionValidator()
        monitoring_validator = MonitoringValidator()
        synthesis_validator = SynthesisValidator()

        planning_phase = PhaseDefinition(
            name=OrchestratorPhase.PLANNING.value,
            description="Create or update work plan AND delegate REMOTE items to agents",
            tools=[create_plan_tool, delegate_tool, list_nodes_tool, time_tool],
            guidance=(
                "PLANNING: Create/update work plan and delegate REMOTE items.\n\n"
                "- CreateOrUpdateWorkPlanTool: define items (LOCAL/REMOTE), dependencies, snake_case IDs\n"
                "- DelegateTaskTool: delegate each REMOTE item immediately after plan creation\n"
                "- For follow-ups: prefer re-delegating to existing items (same work_item_id)\n"
                "  over creating new ones — agent sees full conversation history\n"
                "- Agents work in parallel — leverage this for broad information needs\n"
                "- NO synthesis/compile work items — SYNTHESIS phase handles final answers\n"
                "- DO NOT execute work (EXECUTION phase handles that)\n"
                "- Undelegated REMOTE items will keep you in this phase"
            ),
            max_iterations=self._iteration_limits.planning
        )
        planning_phase.add_validator(planning_validator)

        execution_phase = PhaseDefinition(
            name=OrchestratorPhase.EXECUTION.value,
            description="Execute local work items using domain capabilities",
            tools=[record_execution_tool, time_tool] + domain_tools_list,
            guidance=(
                "EXECUTION: Execute LOCAL work items using domain tools or reasoning.\n\n"
                "For each ready LOCAL item:\n"
                "1. Execute the work (use tools or your own reasoning)\n"
                "2. RecordLocalExecutionTool(item_id, outcome) — marks DONE automatically\n\n"
                "- Skip items with unmet dependencies (they'll appear when unblocked)\n"
                "- Write outcome as a narrative: what you did, results, findings\n"
                "- Do NOT touch REMOTE items (handled in MONITORING)"
            ),
            max_iterations=self._iteration_limits.execution
        )
        execution_phase.add_validator(execution_validator)

        monitoring_phase = PhaseDefinition(
            name=OrchestratorPhase.MONITORING.value,
            description="Interpret responses and execution results, manage work item lifecycle",
            tools=[mark_status_tool, delegate_tool, list_nodes_tool, time_tool],
            guidance=(
                "MONITORING: Review responses and decide next actions.\n\n"
                "For each item with a new response, pick ONE action:\n"
                "- Accept: MarkWorkItemStatusTool(item_id, 'done')\n"
                "- Follow up: DelegateTaskTool(agent, question, work_item_id) — agent sees history\n"
                "- Fail: MarkWorkItemStatusTool(item_id, 'failed')\n\n"
                "DECISION RULE: Mark DONE if the response answers the work item's requirement.\n"
                "Only follow up when critical information is clearly missing, the answer is\n"
                "ambiguous, or the response contains errors that need clarification.\n"
                "Do NOT re-ask for information already provided in the response.\n\n"
                "NEVER call DelegateTaskTool AND MarkWorkItemStatusTool on the same item.\n"
                "If you follow up, the item stays IN_PROGRESS — wait for the next response.\n"
                "You are a COORDINATOR — do not execute work yourself."
            ),
            max_iterations=self._iteration_limits.monitoring
        )
        monitoring_phase.add_validator(monitoring_validator)

        synthesis_phase = PhaseDefinition(
            name=OrchestratorPhase.SYNTHESIS.value,
            description="Create comprehensive answer from all work items regardless of status",
            tools=[],
            guidance=(
                "SYNTHESIS: Create final answer from all completed work.\n\n"
                "- Review ALL items (DONE results, FAILED learnings, IN_PROGRESS partials)\n"
                "- Produce a DIRECT TEXT answer — NO tool calls\n"
                "- Start with the direct answer, then supporting details\n"
                "- Be transparent about completeness and confidence\n"
                "- Extract value even from failures — they contain information"
            ),
            max_iterations=self._iteration_limits.synthesis
        )
        synthesis_phase.add_validator(synthesis_validator)

        phases = [
            planning_phase,
            execution_phase,
            monitoring_phase,
            synthesis_phase,
        ]

        # Create the complete phase system
        return PhaseSystem(
            name="orchestrator",
            description="Complete orchestrator workflow: " + " → ".join(OrchestratorPhase.get_phase_names()),
            phases=phases
        )

    def get_phase_context(self) -> PhaseState:
        """
        Get orchestrator-specific phase context.

        Uses cached snapshot when available (within an iteration),
        otherwise loads fresh data.  Applies _contextualize_status so the
        phase machine always sees an accurate WorkPlanStatus.
        """
        try:
            raw_status = self._snapshot.status
            status = self._contextualize_status(raw_status)
            return create_phase_state(
                work_plan_status=status,
                thread_id=self._thread_id,
                node_uid=self._node_uid
            )
        except Exception as e:
            return create_phase_state(
                thread_id=self._thread_id,
                node_uid=self._node_uid
            )

    def _contextualize_status(self, raw_status):
        """
        Translate orchestration context into accurate plan status.

        The phase machine routes purely on WorkPlanStatus.  This method
        ensures the status reflects the CURRENT situation, not stale
        state from a previous cycle.

        Current adjustment:
          NEW_REQUEST + is_complete + plan not modified this cycle
          → override is_complete to False.  The old plan being "complete"
            is irrelevant — the new request hasn't been addressed yet.
            Once any tool modifies the plan, is_complete naturally updates
            from the real plan state.
        """
        if raw_status is None:
            return raw_status

        from .context.models import CycleTriggerReason

        if not self._current_orch_context:
            return raw_status

        reason = self._current_orch_context.trigger.reason

        if reason == CycleTriggerReason.NEW_REQUEST and raw_status.is_complete:
            if not self._is_plan_modified_this_cycle():
                return raw_status.model_copy(update={"is_complete": False})

        return raw_status

    def _is_plan_modified_this_cycle(self) -> bool:
        """Check whether the work plan has been modified since this cycle started."""
        if self._plan_updated_at_cycle_start is None:
            return False
        plan = self._snapshot.plan
        if not plan:
            return False
        return plan.updated_at != self._plan_updated_at_cycle_start

    def get_initial_phase(self) -> str:
        """
        Get the initial phase for orchestration.

        Orchestrator always starts with planning.
        """
        return OrchestratorPhase.PLANNING.value

    def is_terminal_phase(self, phase_name: str) -> bool:
        """
        Check if phase is terminal.

        SYNTHESIS is the only terminal phase - represents workflow completion.
        Other phases may stay in themselves temporarily (processing, waiting)
        but will eventually transition.

        Args:
            phase_name: Phase name to check

        Returns:
            True if terminal (SYNTHESIS), False otherwise
        """
        return phase_name == OrchestratorPhase.SYNTHESIS.value

    def update_phase(
            self,
            current_phase: str,
            observations: List[Any]
    ) -> str:
        """
        Update phase via PhaseMachine (cascade + iteration logic).

        get_phase_context() applies _contextualize_status automatically,
        so the phase machine always sees accurate state.
        """
        context = self.get_phase_context()
        final_phase = self._phase_machine.update_phase(current_phase, context)

        if final_phase != current_phase:
            if self._context_builder:
                self._context_builder.record_phase_transition(
                    from_phase=current_phase,
                    to_phase=final_phase,
                    reason="cascade",
                )
            self._print_work_plan_after_phase(final_phase)

        return final_phase

    def can_finish_now(self, current_phase: str) -> bool:
        """
        Determine if orchestrator should finish THIS CYCLE now.

        Clean separation of concerns:
        - This method handles CYCLE finishing (waiting for external events)
        - Phase transitions handle moving between phases (EXECUTION → SYNTHESIS)

        Return True only when:
        1. In SYNTHESIS phase (terminal, work done)
        2. Waiting for responses with no actionable work (pause until responses arrive)

        Do NOT return True just because work is complete - let phase transition
        logic handle EXECUTION → SYNTHESIS. Only finish cycle when in SYNTHESIS.

        Args:
            current_phase: Current phase name

        Returns:
            True if should finish cycle, False if more work needed
        """
        try:
            # Get work plan status
            context = self.get_phase_context()
            if not context or not context.work_plan_status:
                # No work plan - allow finish (defensive)
                return True

            status = context.work_plan_status

            # Case 1: In SYNTHESIS phase (terminal - can always finish)
            try:
                current_phase_enum = OrchestratorPhase(current_phase)
                if current_phase_enum == OrchestratorPhase.SYNTHESIS:
                    return True
            except ValueError:
                pass  # Unknown phase, fall through

            # Case 2: Waiting for responses with no actionable work (router flow)
            # Allow finish if:
            # - We have remote items waiting (already delegated)
            # - No responses to process (has_responses=False)
            # - No local work ready to execute (has_local_ready=False)
            # - No remote work ready to delegate (has_remote_ready=False)
            #
            # This means we've delegated everything we can and are waiting
            # for the router to re-invoke us when responses arrive.
            if status.has_remote_waiting:
                if (not status.has_responses
                        and not status.has_local_ready
                        and not status.has_remote_ready):
                    return True

            # Otherwise, keep working (including transitioning to SYNTHESIS if complete)
            return False

        except Exception as e:
            # On error, allow finish (defensive - don't block forever)
            return True

    # _cascade_to_stable and _log_cascade logic is now in PhaseMachine

    def decide_next_phase(
            self,
            current_phase: str,
            context: PhaseState,
            observations: List[Any]
    ) -> str:
        """Delegates to PhaseMachine for all transition logic."""
        return self._phase_machine.decide_next_phase(current_phase, context)

    def _build_validation_context(self, phase_name: str) -> PhaseValidationContext:
        """
        Build orchestrator-specific validation context using cached snapshot.
        """
        phase_state = self.get_phase_context()
        snap = self._snapshot

        return PhaseValidationContext(
            phase_state=phase_state,
            thread_id=self._thread_id,
            node_uid=self._node_uid,
            plan=snap.plan,
            adjacent_nodes=snap.adjacent_nodes
        )

    def _print_work_plan_after_phase(self, phase: str) -> None:
        """Log work plan status after phase transition."""
        try:
            from mas.elements.nodes.common.workload import WorkItemStatus, WorkItemKind

            workspace_service = self._get_workload_service()
            plan = workspace_service.load_work_plan(self._thread_id, self._node_uid)

            if not plan or not plan.items:
                return

            status = workspace_service.get_work_plan_status(self._thread_id, self._node_uid)

            # Compact one-line status (no emojis)
            status_parts = []
            if status.pending_items > 0:
                status_parts.append(f"{status.pending_items} Pending")
            if status.in_progress_items > 0:
                status_parts.append(f"{status.in_progress_items} In Progress")
            if status.done_items > 0:
                status_parts.append(f"{status.done_items} Done")
            if status.failed_items > 0:
                status_parts.append(f"{status.failed_items} Failed")

            extras = []
            if status.blocked_items > 0:
                extras.append(f"{status.blocked_items} Blocked")
            if status.waiting_items > 0:
                extras.append(f"{status.waiting_items} Waiting")

            extra_str = f" [{', '.join(extras)}]" if extras else ""

            # Build full message for single logger call
            lines = [
                "=" * 80,
                f"WORK PLAN after {phase.upper()} ({status.total_items} items)",
                "=" * 80,
                f"Status: {' | '.join(status_parts)}{extra_str}",
            ]

            # Show items compactly
            for item_status in [WorkItemStatus.PENDING, WorkItemStatus.IN_PROGRESS, WorkItemStatus.DONE,
                                WorkItemStatus.FAILED]:
                items = plan.get_items_by_status(item_status)
                if not items:
                    continue

                for item in items:
                    status_label = {
                        WorkItemStatus.PENDING: "[PENDING]",
                        WorkItemStatus.IN_PROGRESS: "[IN_PROGRESS]",
                        WorkItemStatus.DONE: "[DONE]",
                        WorkItemStatus.FAILED: "[FAILED]"
                    }.get(item_status, "")

                    # Compact one-line per item
                    kind = "local" if item.kind == WorkItemKind.LOCAL else f"->{item.assigned_uid}"
                    item_line = f"{status_label} {item.title[:50]}"
                    if len(item.title) > 50:
                        item_line += "..."
                    item_line += f" ({kind})"

                    # Add dependency info
                    if item.dependencies:
                        completed_deps = plan.get_completed_item_ids()
                        dep_status = []
                        for dep_id in item.dependencies:
                            dep_item = plan.items.get(dep_id)
                            if dep_item:
                                dep_title = dep_item.title[:20] + "..." if len(dep_item.title) > 20 else dep_item.title
                                if dep_id in completed_deps:
                                    dep_status.append(f"done:{dep_title}")
                                else:
                                    dep_status.append(f"pending:{dep_title}")
                            else:
                                dep_status.append(f"?{dep_id}")
                        item_line += f" [depends on: {', '.join(dep_status)}]"

                    # Show delegation conversation if present
                    if item.result and item.result.delegations:
                        delegation_count = len(item.result.delegations)
                        processed_count = sum(1 for d in item.result.delegations if d.processed)
                        pending_count = sum(1 for d in item.result.delegations if d.is_pending)
                        unprocessed_count = sum(1 for d in item.result.delegations if d.needs_attention)

                        if delegation_count == 1:
                            latest = item.result.delegations[0]
                            if latest.is_pending:
                                item_line += f"\n      Waiting for response from {latest.delegated_to}"
                            elif latest.needs_attention:
                                resp_preview = latest.response_content[:100].replace('\n',
                                                                                     ' ') if latest.response_content else "No content"
                                item_line += f"\n      NEW: {resp_preview}..."
                            else:
                                resp_preview = latest.response_content[:100].replace('\n',
                                                                                     ' ') if latest.response_content else "No content"
                                item_line += f"\n      Processed: {resp_preview}..."
                        else:
                            item_line += f"\n      {delegation_count} turns ({processed_count} processed, {unprocessed_count} pending, {pending_count} waiting)"
                            latest = item.result.delegations[-1]
                            if latest.is_pending:
                                item_line += f"\n      Latest: Waiting for {latest.delegated_to}"
                            elif latest.needs_attention:
                                resp_preview = latest.response_content[:100].replace('\n',
                                                                                     ' ') if latest.response_content else "No content"
                                item_line += f"\n      Latest: {resp_preview}..."
                            else:
                                resp_preview = latest.response_content[:100].replace('\n',
                                                                                     ' ') if latest.response_content else "No content"
                                item_line += f"\n      Latest: {resp_preview}..."

                    lines.append(f"   {item_line}")

            lines.append("=" * 80)
            logger.debug("\n".join(lines))
        except Exception:
            pass

    def get_dynamic_context_messages(self, phase_name: str) -> List["ChatMessage"]:
        """Delegates to ContextFormatter with tiered context support."""
        snap = self._snapshot
        ws = snap.workspace_service or self._get_workload_service().get_workspace_service()
        return self._context_formatter.build_dynamic_context_messages(
            phase_name=phase_name,
            plan=snap.plan,
            workspace_service=ws,
            orch_context=self._current_orch_context,
            phase_changed=self._phase_changed,
        )

    def get_phase_static_context(self, phase_name: str) -> List[ChatMessage]:
        """Delegates to ContextFormatter for static context."""
        return self._context_formatter.build_static_context(phase_name)

    def build_focused_prompt(self, phase: str, phase_changed: bool) -> str:
        """Delegates to PromptBuilder for all focused-prompt construction."""
        snap = self._snapshot
        return self._prompt_builder.build(
            phase=phase,
            phase_changed=phase_changed,
            plan=snap.plan,
            status=snap.status,
            orch_context=self._current_orch_context,
            user_request=self._current_user_request or "",
        )

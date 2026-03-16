"""
Phase state machine for the orchestrator.

SRP: Responsible ONLY for deciding phase transitions based on WorkPlanStatus.
Does not build prompts, format context, manage tools, or know about triggers.

The provider is responsible for translating orchestration context (triggers,
cycle state) into an accurate WorkPlanStatus BEFORE handing it to this machine.
This keeps routing purely state-driven and generic.

4-Phase Model:
  PLANNING → EXECUTION → MONITORING → SYNTHESIS
"""

import logging
from typing import List, Optional

from mas.elements.nodes.common.agent.phases.phase_protocols import PhaseState
from .models import PhaseIterationLimits, PhaseIterationState

logger = logging.getLogger(__name__)


class OrchestratorPhase:
    """Phase constants for the 4-phase orchestration model."""
    PLANNING = "planning"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    SYNTHESIS = "synthesis"

    _ORDER = [PLANNING, EXECUTION, MONITORING, SYNTHESIS]

    @classmethod
    def get_execution_order(cls) -> List[str]:
        return list(cls._ORDER)

    @classmethod
    def get_phase_names(cls) -> List[str]:
        return list(cls._ORDER)


class PhaseMachine:
    """
    Pure state-driven phase-transition machine.

    Routes based ONLY on WorkPlanStatus fields. Has no knowledge of
    triggers, orchestration context, or iteration counts in routing logic.

    The provider layer is responsible for making WorkPlanStatus accurate
    before each call (e.g. overriding stale is_complete on follow-ups).
    """

    def __init__(
        self,
        iteration_limits: Optional[PhaseIterationLimits] = None,
        max_cascade_transitions: int = 10,
    ):
        self._iteration_limits = iteration_limits or PhaseIterationLimits()
        self._iteration_state = PhaseIterationState()
        self._max_cascade_transitions = max_cascade_transitions

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_phase(self, current_phase: str, context: PhaseState) -> str:
        """
        Determine the next stable phase using cascade logic.

        Increments iteration, cascades until stable, resets on transition.
        """
        self._increment(current_phase)
        final = self._cascade(current_phase, context)

        if final != current_phase:
            self._reset(current_phase)

        return final

    def is_phase_limit_exceeded(self, phase: str) -> bool:
        return self._iteration_state.is_exceeded(phase, self._iteration_limits)

    def get_initial_phase(self) -> str:
        return OrchestratorPhase.PLANNING

    @staticmethod
    def is_terminal(phase: str) -> bool:
        return phase == OrchestratorPhase.SYNTHESIS

    # ------------------------------------------------------------------
    # Core transition logic
    # ------------------------------------------------------------------

    def decide_next_phase(self, current: str, context: PhaseState) -> str:
        """Single-step transition decision based purely on plan status."""
        if not context or not context.work_plan_status:
            return OrchestratorPhase.PLANNING

        status = context.work_plan_status

        if self.is_phase_limit_exceeded(current):
            return self._on_limit_exceeded(current, status)

        if current == OrchestratorPhase.PLANNING:
            return self._decide_from_planning(status)
        elif current == OrchestratorPhase.EXECUTION:
            return self._decide_from_execution(status)
        elif current == OrchestratorPhase.MONITORING:
            return self._decide_from_monitoring(status)
        elif current == OrchestratorPhase.SYNTHESIS:
            return OrchestratorPhase.SYNTHESIS

        return OrchestratorPhase.PLANNING

    # ------------------------------------------------------------------
    # Per-phase decision helpers (pure state-driven, no trigger logic)
    # ------------------------------------------------------------------

    def _decide_from_planning(self, status) -> str:
        """
        Route from PLANNING based purely on actionable work state.

        The provider guarantees that status fields (especially is_complete)
        accurately reflect the current situation before this is called.
        """
        if not status.total_items or status.has_remote_ready:
            return OrchestratorPhase.PLANNING

        if status.has_local_ready:
            return OrchestratorPhase.EXECUTION

        if status.has_responses or status.has_remote_waiting:
            return OrchestratorPhase.MONITORING

        if status.is_complete:
            return OrchestratorPhase.SYNTHESIS

        return OrchestratorPhase.PLANNING

    def _decide_from_execution(self, status) -> str:
        if status.is_complete:
            return OrchestratorPhase.SYNTHESIS
        if status.has_local_ready:
            return OrchestratorPhase.EXECUTION
        return OrchestratorPhase.MONITORING

    def _decide_from_monitoring(self, status) -> str:
        if status.is_complete:
            return OrchestratorPhase.SYNTHESIS
        if status.has_responses:
            return OrchestratorPhase.MONITORING

        # All items blocked with no way forward
        if (status.blocked_items > 0
            and status.pending_items == 0
            and not status.has_local_ready
            and not status.has_remote_waiting):
            logger.warning("All items blocked (%d) - forcing SYNTHESIS", status.blocked_items)
            return OrchestratorPhase.SYNTHESIS

        if status.has_local_ready:
            return OrchestratorPhase.EXECUTION

        # Pending items need planning/delegation
        if status.pending_items > 0:
            return OrchestratorPhase.PLANNING

        return OrchestratorPhase.MONITORING

    # ------------------------------------------------------------------
    # Cascade / iteration helpers
    # ------------------------------------------------------------------

    def _cascade(self, start: str, context: PhaseState) -> str:
        visited = {start}
        current = start

        for _ in range(self._max_cascade_transitions):
            nxt = self.decide_next_phase(current, context)
            if nxt == current:
                return current
            if nxt in visited:
                logger.warning("Cycle detected in cascade (%s -> %s), forcing SYNTHESIS", current, nxt)
                return OrchestratorPhase.SYNTHESIS
            visited.add(nxt)
            current = nxt

        logger.warning("Max cascade transitions reached from %s", start)
        return current

    def _on_limit_exceeded(self, phase: str, status) -> str:
        logger.warning("Phase limit exceeded: %s", phase)

        if phase == OrchestratorPhase.PLANNING:
            if status and status.has_local_ready:
                return OrchestratorPhase.EXECUTION
            if status and (status.has_remote_waiting or status.in_progress_items > 0):
                return OrchestratorPhase.MONITORING
            return OrchestratorPhase.SYNTHESIS

        if phase == OrchestratorPhase.EXECUTION:
            return OrchestratorPhase.MONITORING

        if phase == OrchestratorPhase.MONITORING:
            # Don't abandon pending delegations — stay in MONITORING
            # (the cycle will end naturally, and a new cycle triggers
            # when responses arrive).
            if status and status.has_remote_waiting:
                return OrchestratorPhase.MONITORING
            return OrchestratorPhase.SYNTHESIS

        return OrchestratorPhase.SYNTHESIS

    def _increment(self, phase: str) -> None:
        self._iteration_state = self._iteration_state.increment(phase)

    def _reset(self, phase: str) -> None:
        self._iteration_state = self._iteration_state.reset(phase)

"""
Context formatter for orchestrator LLM interactions.

SRP: Responsible ONLY for formatting workspace/work-plan data
into ChatMessage objects consumed by the strategy's build_context.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from mas.elements.llms.common.chat.message import ChatMessage, Role
from mas.elements.nodes.common.workload import WorkItemStatus, WorkItemKind

logger = logging.getLogger(__name__)


class ContextFormatter:
    """
    Formats workspace state into ChatMessage objects for LLM consumption.

    Stateless – all data is passed via method arguments or the snapshot.
    """

    def __init__(
        self,
        thread_id: str,
        node_uid: str,
        get_adjacent_nodes: Callable[[], Dict],
    ):
        self._thread_id = thread_id
        self._node_uid = node_uid
        self._get_adjacent_nodes = get_adjacent_nodes

    def build_dynamic_context_messages(
        self,
        phase_name: str,
        plan: Any,
        workspace_service: Any,
        orch_context: Any,
        phase_changed: bool = True,
    ) -> List[ChatMessage]:
        """
        Build the dynamic context messages sent before each LLM call.

        Implements tiered context:
        - phase_changed=True  → FULL context (orchestrator context + phase-filtered plan snapshot)
        - phase_changed=False → BRIEF context (status summary + items needing attention only)
        """
        messages: List[ChatMessage] = []

        try:
            if phase_changed:
                content = self._build_full_context(plan, workspace_service, orch_context, phase_name)
            else:
                content = self._build_brief_context(plan, workspace_service, phase_name)

            if logger.isEnabledFor(logging.DEBUG):
                tier = "FULL" if phase_changed else "BRIEF"
                logger.debug("DYNAMIC CONTEXT [%s] (%s): %s", phase_name.upper(), tier, content[:500])

            messages.append(ChatMessage(role=Role.USER, content=content))

        except Exception as e:
            logger.error("Error building dynamic context: %s", e)

        return messages

    def _build_full_context(
        self, plan: Any, workspace_service: Any, orch_context: Any,
        phase_name: str = "",
    ) -> str:
        """Full context with trigger info + phase-filtered plan snapshot."""
        plan_snapshot = (
            self._build_plan_snapshot(plan, workspace_service, phase_name=phase_name)
            if plan else "No work plan exists yet."
        )

        if orch_context:
            return orch_context.format_context(plan_snapshot)
        return f"Current Work Plan:\n{plan_snapshot}"

    def _build_brief_context(
        self, plan: Any, workspace_service: Any, phase_name: str,
    ) -> str:
        """Brief context with only status + actionable items (continuation)."""
        status = workspace_service.get_work_plan_status(self._thread_id, self._node_uid)

        lines = [
            f"[CONTINUATION] Work Plan Status: "
            f"pending={status.pending_items}, in_progress={status.in_progress_items}, "
            f"done={status.done_items}, failed={status.failed_items}, "
            f"complete={status.is_complete}",
        ]

        if not plan or not hasattr(plan, 'items') or not plan.items:
            return "\n".join(lines)

        # Only show items that need attention — full response for quality judgment
        attention_items = []
        for item in plan.items.values():
            if item.result and item.result.delegations:
                for ex in item.result.delegations:
                    if ex.needs_attention:
                        resp = ex.response_content or "No content"
                        attention_items.append(f"  - {item.id}: NEW RESPONSE from {ex.delegated_to}: {resp}")
                        break

        if attention_items:
            lines.append(f"\nItems needing attention ({len(attention_items)}):")
            lines.extend(attention_items)

        # Show ready items for execution/delegation phases
        if phase_name == "execution":
            ready = plan.get_ready_items()
            if ready:
                ready_items = [f"  - {item.id}: {item.title}" for item in ready[:5]]
                lines.append(f"\nReady items ({len(ready)}):")
                lines.extend(ready_items)

        return "\n".join(lines)

    def build_static_context(self, phase_name: str) -> List[ChatMessage]:
        """
        Build phase-specific static context (e.g. adjacent-node descriptions).

        Only PLANNING and MONITORING need node info.
        """
        NEEDS_NODES = {"planning", "monitoring"}
        if phase_name not in NEEDS_NODES:
            return []

        nodes_text = self._format_adjacent_nodes()
        if not nodes_text:
            return []

        return [ChatMessage(role=Role.SYSTEM, content=nodes_text)]

    # ------------------------------------------------------------------
    # Internal formatters
    # ------------------------------------------------------------------

    def _format_adjacent_nodes(self) -> Optional[str]:
        try:
            nodes = self._get_adjacent_nodes()
            if not nodes:
                return None
            lines = ["## Available Agents for Delegation\n"]
            for uid, card in nodes.items():
                lines.append(str(card))
                lines.append("")
            return "\n".join(lines)
        except Exception:
            return None

    def _build_plan_snapshot(
        self,
        plan: Any,
        workspace_service: Any,
        phase_name: str = "",
    ) -> str:
        """
        Build a phase-filtered work-plan snapshot.

        EXECUTION: only LOCAL items (skips REMOTE response content)
        MONITORING: only items with responses needing attention + summary of others
        PLANNING/SYNTHESIS: full plan (needs complete picture)
        """
        status = workspace_service.get_work_plan_status(self._thread_id, self._node_uid)

        lines = [
            f"Work Plan: {status.total_items} items | "
            f"pending={status.pending_items} in_progress={status.in_progress_items} "
            f"done={status.done_items} failed={status.failed_items} | "
            f"complete={status.is_complete}",
        ]

        if not plan:
            return "\n".join(lines)

        lines.append(f"Summary: {plan.summary}")

        all_statuses = [
            WorkItemStatus.PENDING, WorkItemStatus.IN_PROGRESS,
            WorkItemStatus.DONE, WorkItemStatus.FAILED,
        ]

        for item_status in all_statuses:
            items = plan.get_items_by_status(item_status)
            if not items:
                continue

            # EXECUTION: only LOCAL items that are actionable
            if phase_name == "execution":
                if item_status == WorkItemStatus.FAILED:
                    continue
                items = [i for i in items if i.kind == WorkItemKind.LOCAL]
                if not items:
                    continue

            lines.append(f"\n{item_status.value.upper()} ({len(items)}):")
            for item in items:
                info = f"  - {item.title} (ID: {item.id})"
                if item.dependencies:
                    info += f"\n    Dependencies: {item.dependencies}"
                if item.kind == WorkItemKind.REMOTE:
                    info += f" -> {item.assigned_uid}"
                else:
                    info += " [LOCAL]"
                if item.retry_count > 0:
                    info += f" [retries: {item.retry_count}/{item.max_retries}]"
                lines.append(info)

                # FAILED items: show the full error reason
                if item_status == WorkItemStatus.FAILED:
                    if item.error:
                        lines.append(f"    Error: {item.error}")
                    continue

                # EXECUTION: local execution outcome (full)
                if phase_name == "execution":
                    if item.result and item.result.local_execution:
                        outcome = item.result.local_execution.outcome or ""
                        if outcome:
                            lines.append(f"    Execution: {outcome}")
                    continue

                # MONITORING: full response for quality judgment
                if phase_name == "monitoring":
                    if item.result and item.result.delegations:
                        latest = item.result.delegations[-1]
                        if latest.needs_attention:
                            resp = latest.response_content or "No content"
                            lines.append(f"    NEW RESPONSE from {latest.delegated_to}: {resp}")
                        elif latest.is_pending:
                            lines.append(f"    Waiting for {latest.delegated_to}")
                        else:
                            lines.append(f"    Processed ({len(item.result.delegations)} exchanges)")
                    continue

                # PLANNING / SYNTHESIS: full content
                if item.result and item.result.delegations:
                    summary = item.result.conversation_summary(
                        truncate=False, max_chars=250,
                    )
                    for line in summary.split("\n"):
                        lines.append(f"    {line}")
                elif item.result and item.result.local_execution:
                    outcome = item.result.local_execution.outcome or ""
                    if outcome:
                        lines.append(f"    Execution: {outcome}")

        return "\n".join(lines)

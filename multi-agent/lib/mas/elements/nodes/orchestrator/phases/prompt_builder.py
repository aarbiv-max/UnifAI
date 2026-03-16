"""
Prompt builder for orchestrator phases.

SRP: Responsible ONLY for constructing the focused prompt string
that tells the LLM what to do in the current situation.
"""

from typing import Any


class PromptBuilder:
    """
    Builds situation-aware focused prompts for each orchestrator phase.

    Stateless builder – all data is injected via method arguments.
    """

    def build(
        self,
        phase: str,
        phase_changed: bool,
        plan: Any,
        status: Any,
        orch_context: Any,
        user_request: str = "",
    ) -> str:
        """
        Dispatch to the appropriate phase-specific builder.

        Args:
            phase: Current phase name
            phase_changed: Whether the phase just transitioned
            plan: Current WorkPlan (or None)
            status: Current WorkPlanStatus (or None)
            orch_context: OrchestratorContext with trigger info
            user_request: Original user request text
        """
        builders = {
            "planning": self._planning,
            "execution": self._execution,
            "monitoring": self._monitoring,
            "synthesis": self._synthesis,
        }
        builder_fn = builders.get(phase)
        if not builder_fn:
            return ""
        return builder_fn(orch_context, plan, status, phase_changed, user_request)

    # ------------------------------------------------------------------
    # PLANNING
    # ------------------------------------------------------------------

    def _planning(self, ctx, plan, status, changed: bool, req: str) -> str:
        from ..context.models import CycleTriggerReason

        reason = ctx.trigger.reason if ctx else None
        user_request = req or "the request"

        if reason == CycleTriggerReason.NEW_REQUEST and status.total_items == 0:
            return (
                "**NEW REQUEST - CREATE WORK PLAN AND DELEGATE**\n\n"
                f"User asked: \"{user_request}\"\n\n"
                "**Your task:** Create a work plan AND delegate REMOTE items in one step.\n\n"
                "**Steps:**\n"
                "1. Analyze the request to understand information needs\n"
                "2. Review 'Available Agents' section above to see agent capabilities\n"
                "3. For each work item, determine:\n"
                "   - Type: LOCAL (you execute) or REMOTE (delegate to agent)\n"
                "   - Dependencies: Which items must complete first\n"
                "   - Assignment: For REMOTE items, which agent based on their capabilities\n"
                "4. Use `CreateOrUpdateWorkPlanTool` with all items\n"
                "5. **IMMEDIATELY** delegate REMOTE items using `DelegateTaskTool`\n"
                "   - DelegateTaskTool(dst_uid, content, work_item_id) handles assignment automatically\n"
                "   - Delegate all independent REMOTE items in this same iteration\n\n"
                "**COMPREHENSIVE COVERAGE:** When information completeness is important,\n"
                "create work items for multiple agents. Information is often distributed\n"
                "across multiple data sources.\n\n"
                "**DO NOT** create a 'synthesize' or 'compile results' work item — "
                "the SYNTHESIS phase handles the final answer automatically."
            )

        if reason == CycleTriggerReason.NEW_REQUEST and status.is_complete:
            return (
                "**FOLLOW-UP REQUEST**\n\n"
                f"User's follow-up: \"{user_request}\"\n\n"
                f"**Context:** Existing plan has {status.total_items} items (all complete).\n\n"
                "**DECIDE your approach** by reviewing the existing results above:\n\n"
                "**Option A — RE-DELEGATE to existing agent (same work item):**\n"
                "  Use when the follow-up relates to work an agent already did.\n"
                "  `DelegateTaskTool(same_agent_uid, follow_up_question, work_item_id=existing_id)`\n"
                "  The agent sees the full previous conversation — no need to repeat context.\n"
                "  This reuses the thread and resets the item to IN_PROGRESS.\n\n"
                "**Option B — CREATE new work items:**\n"
                "  Use when the follow-up needs entirely new work (different topic or agent).\n"
                "  `CreateOrUpdateWorkPlanTool` + `DelegateTaskTool` for new REMOTE items.\n\n"
                "**Option C — ANSWER directly (no new work):**\n"
                "  Use when existing results already contain the answer.\n"
                "  Just finish — the SYNTHESIS phase will produce the answer.\n\n"
                "**Choose the most efficient path.** Re-delegation is preferred when\n"
                "the follow-up builds on previous work — it preserves context and is faster."
            )

        if reason == CycleTriggerReason.NEW_REQUEST and status.total_items > 0:
            active = status.in_progress_items + status.pending_items + status.waiting_items
            return (
                "**FOLLOW-UP REQUEST (PLAN IN PROGRESS)**\n\n"
                f"User's follow-up: \"{user_request}\"\n\n"
                f"**Context:** Plan has {status.total_items} items "
                f"({status.done_items} done, {active} active, {status.failed_items} failed).\n\n"
                "**DECIDE your approach** by reviewing the plan above:\n\n"
                "**Option A — RE-DELEGATE to an agent (continue conversation):**\n"
                "  Use when the follow-up relates to a DONE or IN_PROGRESS item.\n"
                "  `DelegateTaskTool(agent_uid, follow_up, work_item_id=existing_id)`\n"
                "  Agent sees full conversation history — just ask your question.\n\n"
                "**Option B — ADD new work items:**\n"
                "  Use when the follow-up requires entirely new work.\n"
                "  `CreateOrUpdateWorkPlanTool` + `DelegateTaskTool` for REMOTE items.\n\n"
                "**Option C — WAIT for active work:**\n"
                "  If active items will answer the follow-up, just finish.\n"
                "  Results will be processed when responses arrive.\n\n"
                "**Prefer re-delegation** over creating new items when the follow-up\n"
                "builds on work that was already done or is in progress."
            )

        if reason == CycleTriggerReason.RESPONSE_ARRIVED:
            return (
                "**RESPONSES ARRIVED - REVIEW PLAN**\n\n"
                "New responses have been received. You're in PLANNING phase, which means\n"
                "the system detected that the plan might need updates.\n\n"
                "**Your task:** Review the plan and decide:\n"
                "- Are new work items needed based on responses?\n"
                "- Should failed items be retried with different approach?\n"
                "- Is the plan still appropriate?\n\n"
                "Update plan if needed, or finish to proceed to next phase."
            )

        if not changed:
            return (
                "**CONTINUE PLANNING**\n\n"
                "You're still in PLANNING phase.\n\n"
                "**Options:**\n"
                "- Delegate undelegated REMOTE items using `DelegateTaskTool`\n"
                "- Refine work items or update dependencies\n"
                "- Finish to proceed to next phase (all REMOTE items must be delegated first)"
            )

        return "Review and create/update the work plan. Delegate any REMOTE items."

    # ------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------

    def _execution(self, ctx, plan, status, changed: bool, req: str) -> str:
        from mas.elements.nodes.common.workload import WorkItemKind

        if not plan:
            return "Execute pending LOCAL work items."

        ready = plan.get_ready_items()
        blocked = plan.get_blocked_items()
        local_ready = [i for i in ready if i.kind == WorkItemKind.LOCAL]
        local_blocked = [i for i in blocked if i.kind == WorkItemKind.LOCAL]

        if changed and local_ready:
            details = []
            for item in local_ready[:3]:
                details.append(f"  - `{item.id}`: {item.title}")
            if len(local_ready) > 3:
                details.append(f"  - (+{len(local_ready) - 3} more items)")
            return (
                f"**EXECUTE {len(local_ready)} LOCAL ITEM(S)**\n\n"
                f"Items ready to execute:\n" + "\n".join(details) + "\n\n"
                "**For EACH item:**\n"
                "1. Read the item description carefully\n"
                "2. Execute using your capabilities and available tools\n"
                "3. `RecordLocalExecutionTool(item_id, outcome)`\n"
                "   -> This automatically marks the item as DONE\n\n"
                "**Outcome format:** Describe what you did and the results."
            )

        if changed and not local_ready and not local_blocked:
            return (
                "**NO LOCAL ITEMS TO EXECUTE**\n\n"
                "All LOCAL items already executed or none exist.\n\n"
                "Finish to proceed to next phase."
            )

        if changed and local_blocked and not local_ready:
            names = ", ".join([f"'{i.id}'" for i in local_blocked[:2]])
            if len(local_blocked) > 2:
                names += f" (+{len(local_blocked) - 2} more)"
            return (
                "**LOCAL ITEMS BLOCKED**\n\n"
                f"{len(local_blocked)} items blocked by dependencies: {names}\n\n"
                "Cannot execute until dependencies complete.\n"
                "Finish to proceed (will return when unblocked)."
            )

        if not changed and local_ready:
            return f"**CONTINUE EXECUTION** ({len(local_ready)} remaining)\n\nContinue executing pending LOCAL items."

        if not changed and not local_ready:
            return "**EXECUTION COMPLETE**\n\nAll LOCAL items executed.\n\nFinish to proceed to next phase."

        return "Execute pending LOCAL work items."

    # ------------------------------------------------------------------
    # MONITORING
    # ------------------------------------------------------------------

    def _monitoring(self, ctx, plan, status, changed: bool, req: str) -> str:
        from ..context.models import CycleTriggerReason

        reason = ctx.trigger.reason if ctx else None
        changed_items = ctx.trigger.changed_items if ctx else []

        if not plan:
            return "Review work plan and update item statuses."

        needs_attention = []
        waiting = []
        for item in plan.items.values():
            if item.result and item.result.delegations:
                for ex in item.result.delegations:
                    if ex.needs_attention:
                        needs_attention.append(item)
                        break
                    elif ex.is_pending:
                        waiting.append(item)
                        break

        if reason == CycleTriggerReason.RESPONSE_ARRIVED and len(changed_items) == 1:
            iid = changed_items[0]
            return (
                "**RESPONSE RECEIVED**\n\n"
                f"Agent responded to work item: `{iid}`\n\n"
                "**Decision:**\n"
                f"- **Acceptable?** -> `MarkWorkItemStatusTool('{iid}', 'done')`\n"
                f"- **Needs clarification?** -> `DelegateTaskTool(same agent, question, work_item_id)`\n"
                f"- **Failed/impossible?** -> `MarkWorkItemStatusTool('{iid}', 'failed')`\n\n"
                "Mark DONE if the response answers the requirement — do not re-ask\n"
                "for information already provided. Only follow up if critical info\n"
                "is missing or the answer is ambiguous."
            )

        if reason == CycleTriggerReason.RESPONSE_ARRIVED and len(changed_items) > 1:
            items_list = ", ".join([f"`{i}`" for i in changed_items[:4]])
            if len(changed_items) > 4:
                items_list += f" (+{len(changed_items) - 4} more)"
            return (
                f"**{len(changed_items)} RESPONSES RECEIVED**\n\n"
                f"Items: {items_list}\n\n"
                "**For each response:**\n"
                "1. Does it answer the work item's requirement? -> Mark DONE\n"
                "2. Critical info missing or answer ambiguous? -> Follow up\n"
                "3. Error or impossible? -> Mark FAILED\n\n"
                "Do NOT re-ask for information already provided in a response."
            )

        if changed and reason != CycleTriggerReason.RESPONSE_ARRIVED:
            if needs_attention:
                return (
                    f"**REVIEW {len(needs_attention)} RESPONSE(S)**\n\n"
                    "Local execution complete. Now review responses from delegated work."
                )
            if waiting:
                return (
                    f"**WAITING FOR {len(waiting)} RESPONSE(S)**\n\n"
                    "All actionable work complete. Waiting for agents to respond.\n"
                    "Finish to pause (will resume when responses arrive)."
                )
            return "**NO PENDING RESPONSES**\n\nAll work items processed.\nFinish to proceed to SYNTHESIS."

        if not changed and needs_attention:
            return f"**CONTINUE MONITORING** ({len(needs_attention)} items need attention)\n\nContinue processing remaining responses."

        if not changed and not needs_attention:
            if waiting:
                return (
                    f"**WAITING FOR RESPONSES** ({len(waiting)} items)\n\n"
                    "All available responses processed.\n"
                    "Finish to pause until more responses arrive."
                )
            return "**MONITORING COMPLETE**\n\nAll work items reviewed and processed.\nFinish to proceed to SYNTHESIS."

        return "Review responses and update work item statuses."

    # ------------------------------------------------------------------
    # SYNTHESIS
    # ------------------------------------------------------------------

    def _synthesis(self, ctx, plan, status, changed: bool, req: str) -> str:
        from ..context.models import CycleTriggerReason

        reason = ctx.trigger.reason if ctx else None
        user_request = req or "the request"
        total = status.total_items
        done = status.done_items
        failed = status.failed_items

        if changed and status.is_complete and failed == 0:
            return (
                "**SYNTHESIZE COMPLETE RESULTS**\n\n"
                f"All {total} work items completed successfully!\n\n"
                f"Original request: \"{user_request}\"\n\n"
                "Create comprehensive final response.\n\n"
                "**Include:**\n"
                "1. Direct answer to user's request\n"
                "2. Summary of what was accomplished\n"
                "3. Key findings or results from work items\n"
                "4. Any important details or context\n\n"
                "Then finish to return response to user."
            )

        if changed and (done > 0 or failed > 0):
            return (
                "**SYNTHESIZE PARTIAL RESULTS**\n\n"
                f"Work summary: {done}/{total} done, {failed} failed.\n\n"
                f"Original request: \"{user_request}\"\n\n"
                "Create honest, transparent response.\n\n"
                "**Include:**\n"
                "1. What was successfully accomplished (from DONE items)\n"
                "2. What couldn't be completed and why (from FAILED items)\n"
                "3. Whether partial results answer the request\n"
                "4. Suggestions for next steps if applicable\n\n"
                "Be transparent about limitations.\nThen finish."
            )

        if changed and done == 0 and total > 0:
            if failed == total:
                return (
                    "**SYNTHESIZE FAILURE RESULTS**\n\n"
                    f"Unable to complete any of {total} work items.\n\n"
                    f"Original request: \"{user_request}\"\n\n"
                    "Explain what went wrong.\n\n"
                    "**Include:**\n"
                    "1. Clear explanation of why work couldn't be completed\n"
                    "2. What was attempted\n"
                    "3. Suggestions for alternative approaches\n\n"
                    "Then finish."
                )
            return (
                "**EARLY SYNTHESIS**\n\n"
                "Entered SYNTHESIS but work is still in progress.\n\n"
                "Provide interim update or explain current status.\nThen finish."
            )

        if reason == CycleTriggerReason.NEW_REQUEST:
            return (
                "**USER FOLLOW-UP IN SYNTHESIS**\n\n"
                f"User asked: \"{user_request}\"\n\n"
                "Options:\n"
                "- If clarification -> Answer directly and finish\n"
                "- If needs new work -> Suggest returning to PLANNING"
            )

        if not changed:
            return (
                "**CONTINUE SYNTHESIS**\n\n"
                "Refine your response or add more context.\n"
                "Finish when response is complete.\n\n"
                f"Original request: \"{user_request}\""
            )

        return (
            "Synthesize results and create final response for the user. "
            "Review completed work items and formulate a comprehensive answer."
        )

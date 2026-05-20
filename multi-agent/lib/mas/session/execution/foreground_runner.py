"""
Foreground (in-process) session execution with lifecycle orchestration.

Single ``run()`` entry point with an optional ``stream`` flag:
  - stream=False → blocking execution, returns final GraphState.
  - stream=True  → graph runs on a background thread; events flow
                    through the channel layer and are yielded to the caller.

Streaming is an orthogonal concern handled entirely by the channel:
nodes emit events via SessionChannel, the caller reads them via
SessionChannelReader.  The executor only ever calls ``run()`` — there
is no ``stream()`` on the executor.
"""
import logging
import threading
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from mas.core.channels import ChannelFactory
from mas.core.enums import ResourceCategory
from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig
from mas.elements.tools.sandbox_exec.sandbox_exec import SandboxExecTool
from mas.elements.tools.sandbox_exec.service import SandboxLifecycleService
from mas.graph.state.graph_state import GraphState
from mas.session.execution.lifecycle import SessionLifecycle
from mas.session.domain.workflow_session import WorkflowSession

logger = logging.getLogger(__name__)


class ForegroundSessionRunner:
    """
    Orchestrates synchronous graph execution with session lifecycle hooks.

    Delegates lifecycle transitions (begin / complete / fail) to
    SessionLifecycle.  When streaming, a channel writer+reader pair
    decouples execution from event delivery.
    """

    def __init__(
        self,
        lifecycle: SessionLifecycle,
        channel_factory: ChannelFactory,
        sandbox_lifecycle: Optional[SandboxLifecycleService] = None,
    ) -> None:
        self._lifecycle = lifecycle
        self._channel_factory = channel_factory
        self._sandbox_lifecycle = sandbox_lifecycle

    def run(
        self,
        session: WorkflowSession,
        scope: str = "public",
        stream: bool = False,
    ) -> Union[GraphState, Iterator[Any]]:
        """
        Execute the session graph.

        Args:
            session: Fully hydrated workflow session.
            scope: Visibility scope for this execution.
            stream: If True, returns an event iterator instead of the
                    final state.  The lifecycle is completed internally
                    once execution finishes.

        Returns:
            ``GraphState`` when *stream* is False;
            ``Iterator[Any]`` of channel events when *stream* is True.
        """
        if stream:
            return self._run_streaming(session, scope)
        return self._run_blocking(session, scope)

    # ── Blocking path ────────────────────────────────────────────

    def _run_blocking(
        self,
        session: WorkflowSession,
        scope: str,
    ) -> GraphState:
        self._lifecycle.begin(session.record, scope)
        self._enrich_holder(session)

        sandbox_info = self._provision_sandboxes(session)

        try:
            final_state = session.executable_graph.run(
                session.graph_state, session_id=session.get_run_id(),
            )
        except Exception as e:
            self._lifecycle.fail(session.record, e)
            raise
        else:
            self._lifecycle.complete(session.record, final_state)
            return final_state
        finally:
            self._teardown_sandboxes(sandbox_info, session)
            self._cleanup_tools(session)

    # ── Streaming path ───────────────────────────────────────────

    def _run_streaming(
        self,
        session: WorkflowSession,
        scope: str,
    ) -> Iterator[Any]:
        self._lifecycle.begin(session.record, scope)
        self._enrich_holder(session)

        sandbox_info = self._provision_sandboxes(session)

        channel = self._channel_factory.create(session.get_run_id())
        reader = self._channel_factory.create_reader(session.get_run_id())
        self._inject_channel(session, channel)

        result: dict = {"state": None, "error": None}

        def _execute() -> None:
            try:
                result["state"] = session.executable_graph.run(
                    session.graph_state, session_id=session.get_run_id(),
                )
            except Exception as e:
                result["error"] = e
            finally:
                channel.close()

        thread = threading.Thread(target=_execute, name=f"graph-exec-{session.get_run_id()[:8]}")
        thread.start()

        try:
            yield from reader
        finally:
            channel.close()
            thread.join(timeout=60)
            self._inject_channel(session, None)
            self._teardown_sandboxes(sandbox_info, session)
            self._cleanup_tools(session)

            try:
                if result["error"]:
                    self._lifecycle.fail(session.record, result["error"])
                elif result["state"] is not None:
                    self._lifecycle.complete(session.record, result["state"])
            except Exception:
                logger.exception("Failed to complete session lifecycle")

    # ── Sandbox lifecycle ────────────────────────────────────────

    def _detect_sandbox_needs(
        self, session: WorkflowSession,
    ) -> Optional[Tuple[List[str], SandboxExecToolConfig]]:
        """Find all node UIDs that own a SandboxExecTool and extract one config."""
        registry = session.session_registry
        sandbox_config: Optional[SandboxExecToolConfig] = None

        tool_rids: List[str] = []
        for rid, tool in registry.all_of(ResourceCategory.TOOL).items():
            if isinstance(tool, SandboxExecTool):
                tool_rids.append(rid)
                if sandbox_config is None:
                    sandbox_config = tool._config

        if not tool_rids or sandbox_config is None:
            return None

        agent_ids: List[str] = []
        for step in session.rt_graph_plan.steps:
            agent_ids.append(step.uid)

        if not agent_ids:
            return None

        return agent_ids, sandbox_config

    def _provision_sandboxes(
        self, session: WorkflowSession,
    ) -> Optional[Dict[str, Any]]:
        """Pre-provision sandbox containers if the graph uses them."""
        if self._sandbox_lifecycle is None:
            return None

        info = self._detect_sandbox_needs(session)
        if info is None:
            return None

        agent_ids, config = info
        run_id = session.get_run_id()

        try:
            state = self._sandbox_lifecycle.provision_for_session(
                run_id=run_id,
                agent_ids=agent_ids,
                config=config,
            )
            logger.info(
                "Provisioned %d sandbox containers for run %s",
                len(state.containers), run_id,
            )
            return {
                "run_id": run_id,
                "agent_ids": agent_ids,
                "config": config,
            }
        except Exception:
            logger.exception("Sandbox provisioning failed for run %s", run_id)
            return None

    def _teardown_sandboxes(
        self,
        sandbox_info: Optional[Dict[str, Any]],
        session: WorkflowSession,
    ) -> None:
        """Tear down sandbox containers using naming convention."""
        if self._sandbox_lifecycle is None or sandbox_info is None:
            return
        try:
            self._sandbox_lifecycle.teardown_by_naming(
                run_id=sandbox_info["run_id"],
                agent_ids=sandbox_info["agent_ids"],
                config=sandbox_info["config"],
            )
        except Exception:
            logger.exception(
                "Sandbox teardown failed for run %s", sandbox_info.get("run_id"),
            )

    # ── Context enrichment ───────────────────────────────────────

    @staticmethod
    def _enrich_holder(session: WorkflowSession) -> None:
        """Set the execution context with run_id in tags and inject the holder into nodes."""
        run_ctx = session.record.run_context
        run_id = session.get_run_id()
        enriched = run_ctx.model_copy(update={
            "tags": {**run_ctx.tags, "run_id": run_id},
        })
        session.execution_holder.context = enriched

        holder = session.execution_holder
        for node in session.session_registry.all_of(ResourceCategory.NODE).values():
            if hasattr(node, "set_execution_holder"):
                node.set_execution_holder(holder)

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _inject_channel(session: WorkflowSession, channel) -> None:
        for node in session.session_registry.all_of(ResourceCategory.NODE).values():
            if hasattr(node, "set_streaming_channel"):
                node.set_streaming_channel(channel)

    @staticmethod
    def _cleanup_tools(session: WorkflowSession) -> None:
        """Call cleanup() on every tool that supports it (best-effort)."""
        for rid, tool in session.session_registry.all_of(ResourceCategory.TOOL).items():
            if hasattr(tool, "cleanup"):
                try:
                    tool.cleanup()
                except Exception:
                    logger.exception("Tool cleanup failed for %s", rid)

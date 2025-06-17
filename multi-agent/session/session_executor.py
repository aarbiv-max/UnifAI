from typing import Any, Dict, Iterator, Optional, Union
from session.user_session_manager import UserSessionManager
from session.repository.repository import SessionRepository
from session.workflow_session import WorkflowSession
from graph.state.graph_state import GraphState
from core.context import set_current_context
from .status import SessionStatus
from .utils import derive_title

SessionOrId = Union[WorkflowSession, str]


class SessionExecutor:
    """
    SRP: only handles “run” and “stream” of a WorkflowSession.
    Can accept either a WorkflowSession or a run_id string.
    """

    def __init__(
            self,
            session_manager: UserSessionManager,
            repository: SessionRepository
    ):
        self._sessions = session_manager
        self._repo = repository

    def _resolve_session(self, session_or_id: SessionOrId) -> WorkflowSession:
        """
        If given a WorkflowSession, return it.
        Otherwise treat it as run_id and load via the manager.
        """
        if isinstance(session_or_id, WorkflowSession):
            return session_or_id

        run_id = session_or_id
        session = self._sessions.get_session(run_id)
        return session

    def _pre_run(self, session: WorkflowSession, inputs: Dict[str, Any], scope: str) -> None:
        """
        1) add title to session metadata
        2) bind RunContext into ContextVar
        3) seed input into the GraphState
        4) mark context as running
        5) update status
        6) persist
        """
        if session.metadata.title is None:
            if title := derive_title(inputs):
                session.metadata.title = title
        ctx = session.run_context.change_scope(scope)  # TODO remove scope parameter from context
        set_current_context(ctx)
        session.graph_state.update(inputs)
        session.update_status(SessionStatus.RUNNING)
        self._repo.save(session)

    def _post_run(self, session: WorkflowSession, final_state) -> None:
        """
        1) attach final state
        2) mark context finished
        3) re‐bind new context
        4) update status
        5) persist
        """
        session.graph_state = GraphState(**final_state)
        session.run_context = session.run_context.mark_finished()
        set_current_context(session.run_context)
        session.update_status(SessionStatus.COMPLETED)
        self._repo.save(session)

    def _error_run(self, session: WorkflowSession, error: Exception) -> None:
        """
        1) attach error state
        2) mark context finished
        3) update status
        4) persist
        """
        session.run_context = session.run_context.mark_finished()
        session.update_status(SessionStatus.FAILED)
        self._repo.save(session)

    def run(
            self,
            session_or_id: SessionOrId,
            inputs: Dict[str, Any],
            scope: str = "public"
    ) -> GraphState:
        """
        Run the graph to completion and return the final GraphState.
        """
        session = self._resolve_session(session_or_id)
        self._pre_run(session, inputs, scope)
        try:
            final_state = session.executable_graph.run(session.graph_state)
        except Exception as e:
            self._error_run(session, e)
            raise e

        self._post_run(session, final_state)
        return final_state

    def stream(
            self,
            session_or_id: SessionOrId,
            inputs: Dict[str, Any],
            scope: str = "public",
            **stream_kwargs: Any
    ) -> Iterator[Any]:
        """
        Stream execution chunks, then persist at the end.
        """
        session = self._resolve_session(session_or_id)
        self._pre_run(session, inputs, scope)

        try:
            for chunk in session.executable_graph.stream(
                    session.graph_state,
                    **stream_kwargs
            ):
                yield chunk
                try:
                    # will work only if custom is enabled in stream_kwargs
                    session.graph_state = chunk[1].get("state") if isinstance(chunk, (list, tuple)) and isinstance(
                        chunk[1], dict) else None
                except Exception as e:
                    raise e

        except Exception as e:
            self._error_run(session, e)
            raise e

        # once the generator ends, finalize
        self._post_run(session, session.graph_state)

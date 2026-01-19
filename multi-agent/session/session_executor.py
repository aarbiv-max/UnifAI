from typing import Any, Dict, Iterator, Optional, Union
from session.user_session_manager import UserSessionManager
from session.repository.repository import SessionRepository
from session.repository.stop_signal_repository import StopSignalRepository
from session.workflow_session import WorkflowSession
from graph.state.graph_state import GraphState
from core.context import set_current_context
from core.channels import SessionChannel
from core.stop_signal_context import (
    set_stop_signal_checker,
    clear_stop_signal_checker,
    StoppedExecutionError
)
from engine.channels import LangGraphEmitter
from session.channels import LocalSessionChannel
from .status import SessionStatus
from .utils import derive_title

SessionOrId = Union[WorkflowSession, str]


class SessionExecutor:
    """
    SRP: only handles "run" and "stream" of a WorkflowSession.
    Can accept either a WorkflowSession or a run_id string.
    """

    def __init__(
            self,
            session_manager: UserSessionManager,
            repository: SessionRepository,
            stop_signal_repo: Optional[StopSignalRepository] = None
    ):
        self._sessions = session_manager
        self._repo = repository
        self._stop_signal_repo = stop_signal_repo

    def _pre_run(
            self,
            session: WorkflowSession,
            inputs: Dict[str, Any],
            scope: str,
            logged_in_user: str,
            streaming: bool = False
    ) -> Optional[SessionChannel]:
        """
        1) add title to session metadata
        2) bind RunContext into ContextVar
        3) seed input into the GraphState
        4) if streaming, create channel and prepare nodes
        5) update status
        6) persist
        
        Returns:
            SessionChannel if streaming=True, None otherwise
        """
        if session.metadata.title is None:
            if title := derive_title(inputs):
                session.metadata.title = title
        ctx = session.run_context.change_scope(scope)  # TODO remove scope parameter from context
        ctx = ctx.set_logged_in_user(logged_in_user)  # TODO remove logged_in_user parameter from context
        set_current_context(ctx)
        session.graph_state.update(inputs)
        
        # Streaming setup - create channel and prepare nodes
        channel = None
        if streaming:
            channel = self._create_streaming_channel(session)
            session.prepare_for_streaming(channel)
        
        session.update_status(SessionStatus.RUNNING)
        self._repo.save(session)
        
        return channel

    def _post_run(
            self,
            session: WorkflowSession,
            final_state,
            streaming: bool = False,
            channel: Optional[SessionChannel] = None
    ) -> None:
        """
        1) attach final state
        2) if streaming, cleanup channel from nodes and close channel
        3) mark context finished
        4) update status
        5) persist
        """
        session.graph_state = GraphState(**final_state)
        
        # Streaming cleanup
        if streaming:
            session.cleanup_streaming()
            if channel:
                channel.close()
        
        session.run_context = session.run_context.mark_finished()
        set_current_context(session.run_context)
        session.update_status(SessionStatus.COMPLETED)
        self._repo.save(session)

    def _error_run(
            self,
            session: WorkflowSession,
            error: Exception,
            streaming: bool = False,
            channel: Optional[SessionChannel] = None
    ) -> None:
        """
        1) if streaming, cleanup channel from nodes and close channel
        2) mark context finished
        3) update status
        4) persist
        """
        if streaming:
            session.cleanup_streaming()
            if channel:
                channel.close()
        
        session.run_context = session.run_context.mark_finished()
        session.update_status(SessionStatus.FAILED)
        self._repo.save(session)

    def _stopped_run(
            self,
            session: WorkflowSession,
            streaming: bool = False,
            channel: Optional[SessionChannel] = None
    ) -> None:
        """
        Handle user-initiated stop of a running session.
        
        Similar to _post_run but:
        1) Sets status to STOPPED instead of COMPLETED
        2) Clears the stop signal to prevent affecting future runs
        3) Preserves current graph_state for potential resumption
        
        Steps:
        1) if streaming, cleanup channel from nodes and close channel
        2) mark context finished
        3) update status to STOPPED
        4) persist current state
        5) clear stop signal
        """
        if streaming:
            session.cleanup_streaming()
            if channel:
                channel.close()
        
        session.run_context = session.run_context.mark_finished()
        session.update_status(SessionStatus.STOPPED)
        self._repo.save(session)
        
        # Clear the stop signal to prevent it from affecting future executions
        if self._stop_signal_repo:
            self._stop_signal_repo.clear_signal(session.get_run_id())

    def _create_stopped_event(self, session: WorkflowSession) -> tuple:
        """
        Create a stopped event to send to the frontend via stream.
        
        Returns a tuple in the format expected by the streaming protocol:
        ("custom", {event_data})
        """
        return ("custom", {
            "type": "workflow_stopped",
            "node": "__system__",
            "display_name": "System",
            "session_id": session.get_run_id(),
            "message": "Workflow stopped by user",
            "state": session.graph_state.get_streamable_state() if session.graph_state else {}
        })

    def _check_stop_signal(self, session_id: str) -> bool:
        """
        Check if a stop signal has been set for this session.
        
        Returns False if no stop signal repository is configured.
        """
        if self._stop_signal_repo is None:
            return False
        return self._stop_signal_repo.check_signal(session_id)

    def run(
            self,
            session: WorkflowSession,
            inputs: Dict[str, Any],
            scope: str = "public",
            logged_in_user=""
    ) -> GraphState:
        """
        Run the graph to completion and return the final GraphState.
        """
        self._pre_run(session, inputs, scope, logged_in_user, streaming=False)
        try:
            final_state = session.executable_graph.run(session.graph_state)
        except Exception as e:
            self._error_run(session, e, streaming=False)
            raise e

        self._post_run(session, final_state, streaming=False)
        return final_state

    def stream(
            self,
            session: WorkflowSession,
            inputs: Dict[str, Any],
            scope: str = "public",
            logged_in_user: str = "",
            **stream_kwargs: Any
    ) -> Iterator[Any]:
        """
        Stream execution chunks, then persist at the end.
        
        Checks for stop signals on each iteration. If a stop signal is detected,
        emits a stopped event and gracefully exits the generator.
        
        Also sets up a stop signal context that can be checked at deeper levels
        (AgentIterator, tool execution, etc.) for more responsive stopping.
        """
        channel = self._pre_run(session, inputs, scope, logged_in_user, streaming=True)
        session_id = session.get_run_id()

        # Set up stop signal checker in context for nested components
        # This allows AgentIterator and other components to check for stop signals
        def check_stop() -> bool:
            return self._check_stop_signal(session_id)
        
        set_stop_signal_checker(check_stop)

        try:
            for chunk in session.executable_graph.stream(
                    session.graph_state,
                    **stream_kwargs
            ):
                # Check for stop signal before yielding each chunk
                if self._check_stop_signal(session_id):
                    # Emit stopped event so frontend knows what happened
                    yield self._create_stopped_event(session)
                    # Handle cleanup with STOPPED status
                    self._stopped_run(session, streaming=True, channel=channel)
                    # Exit generator gracefully
                    return
                
                yield chunk
                try:
                    # will work only if custom is enabled in stream_kwargs
                    # Only update graph_state if we actually get a new state (don't overwrite with None)
                    if isinstance(chunk, (list, tuple)) and isinstance(chunk[1], dict):
                        new_state = chunk[1].get("state")
                        if new_state is not None:
                            session.graph_state = new_state
                except Exception as e:
                    raise e
            
            # Generator completed normally - finalize
            self._post_run(session, session.graph_state, streaming=True, channel=channel)

        except StoppedExecutionError:
            # Execution was stopped from within (e.g., AgentIterator)
            yield self._create_stopped_event(session)
            self._stopped_run(session, streaming=True, channel=channel)
        except GeneratorExit:
            # Consumer stopped iterating early - still need to cleanup
            self._post_run(session, session.graph_state, streaming=True, channel=channel)
            raise
        except Exception as e:
            self._error_run(session, e, streaming=True, channel=channel)
            raise e
        finally:
            # Always clear the stop signal checker
            clear_stop_signal_checker()

    def _create_streaming_channel(self, session: WorkflowSession) -> SessionChannel:
        """
        Factory method for creating the streaming channel.
        Override or extend for different channel types (e.g., Redis).
        """
        emitter = LangGraphEmitter()
        return LocalSessionChannel(
            session_id=session.get_run_id(),
            emitter=emitter
        )

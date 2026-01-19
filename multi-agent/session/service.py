from typing import Any, Dict, Iterator, List, Optional, Union
from .user_session_manager import UserSessionManager
from .session_executor import SessionExecutor
from .workflow_session import WorkflowSession
from .dto import ChatHistoryItem, StopSessionResult
from .models import SessionMeta
from .status import SessionStatus
from .exceptions import BlueprintNotFoundError
from .repository.stop_signal_repository import StopSignalRepository
from core.dto import GroupedCount


class SessionService:
    """
    A service to handle session lifecycle: creation, execution, streaming, and listing.
    """

    def __init__(
        self, 
        manager: UserSessionManager, 
        executor: SessionExecutor,
        stop_signal_repo: Optional[StopSignalRepository] = None
    ):
        self._manager = manager
        self._executor = executor
        self._stop_signal_repo = stop_signal_repo

    def create(self, user_id: str, blueprint_id: str, metadata: Dict[str, Any] | SessionMeta | None = None) -> WorkflowSession:
        """
        Create a new session and return its object (with run_id).
        """
        return self._manager.create_session(
            user_id=user_id,
            blueprint_id=blueprint_id,
            metadata=SessionMeta.model_validate(metadata or {})
        )

    def run(self, session: WorkflowSession, inputs: Dict[str, Any], scope: str = "public", logged_in_user="") -> Any:
        """
        Execute the session to completion, returning the final result.
        """
        return self._executor.run(
            session=session,
            inputs=inputs or {},
            scope=scope,
            logged_in_user=logged_in_user
        )

    def stream(self, session: WorkflowSession, inputs: Dict[str, Any], stream_mode: list = None,
               scope: str = "public", logged_in_user="") -> \
            Iterator[Any]:
        """
        Execute the session in streaming mode, yielding chunks.
        """

        return self._executor.stream(
            session=session,
            inputs=inputs or {},
            stream_mode=stream_mode,
            scope=scope,
            logged_in_user=logged_in_user
        )

    def execute(self, session_id: str, inputs: Dict[str, Any], stream: bool = False,
                stream_mode: list = None, scope: str = "public", logged_in_user="") -> Any:
        """
        Execute an existing session by run_id or session object.

        :param session_id:  session id.
        :param inputs: Input data for execution.
        :param stream: Whether to stream output.
        :param stream_mode: List of modes for streaming.
        :return: Final result or iterator of chunks.
        """
        session = self._manager.get_session(session_id)
        if stream:
            return self.stream(session=session, inputs=inputs, stream_mode=stream_mode, scope=scope, logged_in_user=logged_in_user)
        return self.run(session=session, inputs=inputs, scope=scope, logged_in_user=logged_in_user)

    def list_for_user(self, user_id: str) -> list:
        """
        List all sessions created by a user.
        """
        return self._manager.list_sessions_ids(user_id)

    def get(self, run_id: str) -> WorkflowSession:
        """
        Fetch a session object by its run_id.
        """
        return self._manager.get_session(run_id)

    def get_status(self, run_id: str) -> str:
        """
        Get the status of a session by its run_id.
        """
        session_doc = self._manager.get_doc(run_id)
        return session_doc.get("status", None)

    def get_state(self, run_id: str) -> Dict[str, Any]:
        """
        Get the status of a session by its run_id.
        """
        session_doc = self._manager.get_doc(run_id)
        return session_doc.get("graph_state", None)

    def get_user_sessions_chat_history(self, user_id: str) -> list:
        """
        Get chat history for all sessions created by a user.
        """
        docs = self._manager.list_docs(user_id)
        chat_items = []

        for doc in docs:
            blueprint_id = doc.get("blueprint_id", "")
            # Check if blueprint still exists
            blueprint_exists = self._manager.blueprint_exists(blueprint_id) if blueprint_id else False

            public_usage_scope = False
            if blueprint_exists and blueprint_id:
                source = doc.get("metadata", {}).get("source", "")
                if source == "public_link":
                    try:
                        blueprint_doc = self._manager._bp_service.get_blueprint_draft_doc(blueprint_id)
                        bp_metadata = blueprint_doc.get("metadata", {})
                        public_usage_scope = bp_metadata.get("usageScope") == "public"
                    except (KeyError, Exception):
                        public_usage_scope = False

            chat_item = ChatHistoryItem.from_doc(doc, blueprint_exists=blueprint_exists, public_usage_scope=public_usage_scope)

            chat_items.append(chat_item)

        return chat_items

    def get_user_blueprints(self, user_id) -> List[str]:
        """
        Get all blueprints created by a user.
        """
        docs = self._manager.list_docs(user_id)
        return list({d.get("blueprint_id") for d in docs})

    def group_count(
        self,
        user_id: str,
        group_by: List[str],
        filter: Dict[str, Any] = None
    ) -> List[GroupedCount]:
        """
        Group sessions by specified fields and return counts.
        Performs efficient server-side grouping via the session manager.
        
        Args:
            user_id: The user ID to filter by
            group_by: List of field names to group by (e.g., ["blueprint_id"])
            filter: Optional additional filter criteria
            
        Returns:
            List of GroupedCount DTOs with grouped field values and count.
            Example: [GroupedCount(fields={"blueprint_id": "bp-123"}, count=10), ...]
        """
        return self._manager.group_count(user_id, group_by, filter)

    def count(self, user_id: str, filter: Dict[str, Any] = None) -> int:
        """Count sessions matching filter criteria for a user."""
        return self._manager.count(user_id, filter)

    def delete(self, run_id: str) -> bool:
        """
        Delete a session by run_id. Returns True if deleted, False if not found.
        """
        return self._manager.delete_session(run_id)

    def stop_session(self, session_id: str) -> StopSessionResult:
        """
        Stop a running session by setting a stop signal.
        
        The stop signal will be picked up by the worker executing the session,
        which will gracefully stop the execution and set status to STOPPED.
        
        Args:
            session_id: The session to stop
            
        Returns:
            StopSessionResult indicating success/failure and details
        """
        # Check if stop signal repository is configured
        if self._stop_signal_repo is None:
            return StopSessionResult(
                session_id=session_id,
                success=False,
                previous_status="UNKNOWN",
                message="Stop signal repository not configured"
            )
        
        # Get current status
        try:
            current_status = self.get_status(session_id)
        except KeyError:
            return StopSessionResult(
                session_id=session_id,
                success=False,
                previous_status="NOT_FOUND",
                message=f"Session not found: {session_id}"
            )
        
        # Validate session is running
        if current_status != SessionStatus.RUNNING.name:
            return StopSessionResult(
                session_id=session_id,
                success=False,
                previous_status=current_status,
                message=f"Session is not running (status: {current_status})"
            )
        
        # Set stop signal
        self._stop_signal_repo.set_signal(session_id)
        
        return StopSessionResult(
            session_id=session_id,
            success=True,
            previous_status=current_status,
            message="Stop signal sent. Session will stop shortly."
        )
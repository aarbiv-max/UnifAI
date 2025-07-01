from typing import Any, Dict, Iterator, List
from .user_session_manager import UserSessionManager
from .session_executor import SessionExecutor
from schemas.blueprint.blueprint import BlueprintSpec
from .workflow_session import WorkflowSession
from .dto import ChatHistoryItem
from .models import SessionMeta


class SessionService:
    """
    A service to handle session lifecycle: creation, execution, streaming, and listing.
    """

    def __init__(self, manager: UserSessionManager, executor: SessionExecutor):
        self._manager = manager
        self._executor = executor

    def create(self, user_id: str, blueprint_spec: BlueprintSpec, blueprint_id: str,
               metadata: SessionMeta = None) -> Any:
        """
        Create a new session and return its object (with run_id).
        """
        # TODO, should metadata get from UI? maybe just tags
        return self._manager.create_session(
            user_id=user_id,
            blueprint_spec=blueprint_spec,
            blueprint_id=blueprint_id,
            metadata=metadata or SessionMeta()
        )

    def run(self, session_or_id: Any, inputs: Dict[str, Any], scope: str = "public", logged_in_user="") -> Any:
        """
        Execute the session to completion, returning the final result.
        """
        return self._executor.run(
            session_or_id=session_or_id,
            inputs=inputs or {},
            scope=scope,
            logged_in_user=logged_in_user
        )

    def stream(self, session_or_id: Any, inputs: Dict[str, Any], stream_mode: list = None, scope: str = "public",
               logged_in_user="") -> \
            Iterator[Any]:
        """
        Execute the session in streaming mode, yielding chunks.
        """
        return self._executor.stream(
            session_or_id=session_or_id,
            inputs=inputs or {},
            stream_mode=stream_mode,
            scope=scope,
            logged_in_user=logged_in_user
        )

    def execute(self, session_or_id: Any, inputs: Dict[str, Any], stream: bool = False,
                stream_mode: list = None, scope: str = "public", logged_in_user="") -> Any:
        """
        Execute an existing session by run_id or session object.

        :param session_or_id: Session object or run_id.
        :param inputs: Input data for execution.
        :param stream: Whether to stream output.
        :param stream_mode: List of modes for streaming.
        :return: Final result or iterator of chunks.
        """
        if stream:
            return self.stream(session_or_id=session_or_id, inputs=inputs, stream_mode=stream_mode, scope=scope, logged_in_user=logged_in_user)
        return self.run(session_or_id=session_or_id, inputs=inputs, scope=scope, logged_in_user=logged_in_user)

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
        return [ChatHistoryItem.from_doc(d) for d in docs]

    def get_user_blueprints(self, user_id) -> List[str]:
        """
        Get all blueprints created by a user.
        """
        docs = self._manager.list_docs(user_id)
        return list({d.get("blueprint_id") for d in docs})

"""
WorkloadCapableMixin for thread and workspace management.

Provides nodes with easy access to Thread/Workspace functionality
through the StateBoundWorkloadService integrated with GraphState.
"""

from typing import ClassVar, Optional, Dict, Any, List
from graph.state.graph_state import Channel
from ..workload import StateBoundWorkloadService, Thread, ThreadStatus, Workspace, AgentResult
from elements.llms.common.chat.message import ChatMessage


class WorkloadCapableMixin:
    """
    Mixin that provides workload management capabilities to nodes.
    
    Adds thread and workspace management through StateBoundWorkloadService
    integrated with the existing GraphState system.
    """

    # Channel permissions for workload management
    MIXIN_READS: ClassVar[set[str]] = {Channel.THREADS, Channel.WORKSPACES, Channel.TASK_THREADS}
    MIXIN_WRITES: ClassVar[set[str]] = {Channel.THREADS, Channel.WORKSPACES, Channel.TASK_THREADS}

    def __init__(self, **kwargs):
        """Initialize mixin and call super() for proper MRO."""
        super().__init__(**kwargs)

    def get_workload_service(self) -> StateBoundWorkloadService:
        """
        Get the workload service bound to current state.
        
        Returns:
            StateBoundWorkloadService instance for thread/workspace operations
        """
        state = self.get_state()
        return StateBoundWorkloadService(state)

    # ========== THREAD MANAGEMENT HELPERS ==========

    def create_thread(self, title: str, objective: str) -> Thread:
        """Create a new thread with this node as initiator."""
        service = self.get_workload_service()
        return service.create_thread(title, objective, self.uid)

    def create_child_thread(self, parent_thread: Thread, title: str, objective: str) -> Thread:
        """
        Create a child thread using SOLID pattern.
        
        Args:
            parent_thread: Parent Thread object
            title: Child thread title
            objective: Child thread objective
            
        Returns:
            Created and saved child Thread
        """
        # Thread creates its own child
        child_thread = parent_thread.create_child(title, objective, self.uid)

        # Service only handles persistence
        service = self.get_workload_service()
        return service.save_thread(child_thread)

    def save_thread(self, thread: Thread) -> Thread:
        """Save a thread using the workload service."""
        service = self.get_workload_service()
        return service.save_thread(thread)

    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get a thread by ID."""
        service = self.get_workload_service()
        return service.get_thread(thread_id)

    def update_thread(self, thread: Thread) -> Thread:
        """Update a thread."""
        service = self.get_workload_service()
        return service.update_thread(thread)

    def complete_thread(self, thread_id: str) -> bool:
        """Mark a thread as completed."""
        service = self.get_workload_service()
        return service.complete_thread(thread_id)

    def fail_thread(self, thread_id: str) -> bool:
        """Mark a thread as failed."""
        service = self.get_workload_service()
        return service.fail_thread(thread_id)

    def join_thread(self, thread_id: str) -> bool:
        """Join this node as a participant in a thread."""
        service = self.get_workload_service()
        return service.add_participant(thread_id, self.uid)

    def leave_thread(self, thread_id: str) -> bool:
        """Remove this node as a participant from a thread."""
        service = self.get_workload_service()
        return service.remove_participant(thread_id, self.uid)

    # ========== WORKSPACE MANAGEMENT HELPERS ==========

    def get_workspace(self, thread_id: str) -> Workspace:
        """Get the workspace for a thread."""
        service = self.get_workload_service()
        return service.get_workspace(thread_id)

    def add_result_to_workspace(self, thread_id: str, agent_result: AgentResult) -> None:
        """Add agent result to a workspace."""
        service = self.get_workload_service()
        service.add_result(thread_id, agent_result)

    def add_fact_to_workspace(self, thread_id: str, fact: str) -> None:
        """Add a fact to a workspace."""
        service = self.get_workload_service()
        service.add_fact(thread_id, fact)

    def set_workspace_variable(self, thread_id: str, key: str, value: Any) -> None:
        """Set a variable in a workspace."""
        service = self.get_workload_service()
        service.set_variable(thread_id, key, value)

    def get_workspace_variable(self, thread_id: str, key: str, default: Any = None) -> Any:
        """Get a variable from a workspace."""
        service = self.get_workload_service()
        return service.get_variable(thread_id, key, default)

    def add_artifact_to_workspace(self, thread_id: str, name: str, artifact_type: str,
                                  location: str, metadata: Dict[str, Any] = None) -> None:
        """Add an artifact to a workspace."""
        service = self.get_workload_service()
        service.add_artifact(thread_id, name, artifact_type, location, self.uid, metadata)

    # ========== CONTEXT HELPERS ==========

    def get_thread_context(self, thread_id: str) -> Dict[str, Any]:
        """Get complete context for a thread (thread + workspace + task messages)."""
        service = self.get_workload_service()
        return service.get_context(thread_id)

    def get_workspace_summary(self, thread_id: str) -> Dict[str, Any]:
        """Get a summary of workspace contents."""
        workspace = self.get_workspace(thread_id)
        return workspace.get_context_summary()

    def get_workspace_context(self, thread_id: str) -> 'WorkspaceContext':
        """Get complete workspace context."""
        service = self.get_workload_service()
        return service.get_workspace_context(thread_id)

    # ========== QUERY HELPERS ==========

    def list_my_active_threads(self) -> List[Thread]:
        """List all active threads where this node is a participant."""
        service = self.get_workload_service()
        all_active = service.list_active_threads()
        return [thread for thread in all_active if self.uid in thread.participants]

    def list_threads_by_status(self, status: ThreadStatus) -> List[Thread]:
        """List threads with a specific status."""
        service = self.get_workload_service()
        all_threads = service.list_threads()
        return [thread for thread in all_threads if thread.status == status]

    def get_thread_statistics(self) -> Dict[str, Any]:
        """Get workload statistics."""
        service = self.get_workload_service()
        return service.get_statistics()

    # ========== INTEGRATION HELPERS ==========

    def sync_task_thread_to_workspace(self, thread_id: str) -> None:
        """
        Sync messages from task_threads to workspace facts.
        
        Useful for ensuring workspace has visibility into conversation history.
        """
        state = self.get_state()
        task_threads = state.get(Channel.TASK_THREADS, {})

        if thread_id in task_threads:
            messages = task_threads[thread_id]
            workspace = self.get_workspace(thread_id)

            # Add conversation summary as facts
            for i, msg in enumerate(messages[-5:]):  # Last 5 messages
                fact = f"Message {i + 1}: {msg.role.value}: {msg.content[:100]}..."
                if not workspace.has_fact(fact):
                    workspace.add_fact(fact)

            self.get_workload_service().update_workspace(workspace)

    # ========== CONVERSATION HISTORY HELPERS ==========

    def add_message_to_workspace(self, thread_id: str, message: ChatMessage) -> None:
        """Add a message to workspace conversation history."""
        workspace = self.get_workspace(thread_id)
        workspace.add_message(message)
        self.get_workload_service().update_workspace(workspace)

    def add_messages_to_workspace(self, thread_id: str, messages: List[ChatMessage]) -> None:
        """Add multiple messages to workspace conversation history."""
        workspace = self.get_workspace(thread_id)
        workspace.add_messages(messages)
        self.get_workload_service().update_workspace(workspace)

    def copy_graphstate_messages_to_workspace(self, thread_id: str) -> None:
        """
        Copy all messages from GraphState to workspace conversation history.
        
        Creates a clean copy of all current messages in GraphState.
        """
        state = self.get_state()
        graphstate_messages = state.get(Channel.MESSAGES, [])

        if graphstate_messages:
            workspace = self.get_workspace(thread_id)
            workspace.copy_messages_from_graphstate(graphstate_messages)
            self.get_workload_service().update_workspace(workspace)

    def sync_graphstate_messages_to_workspace(self, thread_id: str) -> None:
        """
        Sync new messages from GraphState to workspace, avoiding duplicates.
        
        Useful for incremental updates when new messages are added to GraphState.
        """
        state = self.get_state()
        graphstate_messages = state.get(Channel.MESSAGES, [])

        if graphstate_messages:
            workspace = self.get_workspace(thread_id)
            workspace.append_messages_from_graphstate(graphstate_messages)
            self.get_workload_service().update_workspace(workspace)

    def get_workspace_conversation_summary(self, thread_id: str) -> Dict[str, Any]:
        """Get conversation summary from workspace."""
        workspace = self.get_workspace(thread_id)
        return workspace.get_conversation_summary()

    def get_recent_workspace_messages(self, thread_id: str, count: int = 10) -> List[ChatMessage]:
        """Get recent messages from workspace conversation history."""
        workspace = self.get_workspace(thread_id)
        return workspace.get_recent_messages(count)

    def clear_workspace_conversation(self, thread_id: str) -> None:
        """Clear conversation history from workspace."""
        workspace = self.get_workspace(thread_id)
        workspace.clear_conversation_history()
        self.get_workload_service().update_workspace(workspace)

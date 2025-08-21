"""
StateBoundWorkloadService for GraphState integration.

SOLID service implementation that integrates Thread/Workspace management
with the existing GraphState system. Provides seamless access to workload
management through StateView for nodes.
"""

from typing import Dict, Any, Optional, List
from graph.state.state_view import StateView
from graph.state.graph_state import Channel
from .interfaces import IWorkloadService
from .thread import Thread, ThreadStatus
from .workspace import Workspace
from .models import AgentResult


class StateBoundWorkloadService(IWorkloadService):
    """
    State-bound implementation of IWorkloadService for GraphState integration.
    
    Integrates Thread/Workspace management with the existing GraphState system.
    Works through StateView to respect channel permissions and state management.
    """
    
    def __init__(self, state: StateView):
        """Initialize with a StateView for channel access."""
        self._state = state
    
    # ========== THREAD MANAGEMENT ==========
    
    def create_thread(self, title: str, objective: str, initiator: str) -> Thread:
        """
        Create a new thread in the GraphState.
        
        Args:
            title: Thread title
            objective: Thread objective/goal
            initiator: ID of the initiating agent
            
        Returns:
            Created Thread instance
        """
        # Create thread
        thread = Thread.create(title, objective, initiator)
        
        # Get current threads from state
        threads = self._state.get(Channel.THREADS, {})
        
        # Save thread to state
        threads[thread.thread_id] = thread.model_dump()
        self._state[Channel.THREADS] = threads
        
        # Create associated workspace
        workspace = Workspace.create(thread.thread_id)
        workspaces = self._state.get(Channel.WORKSPACES, {})
        workspaces[thread.thread_id] = workspace.model_dump()
        self._state[Channel.WORKSPACES] = workspaces
        
        return thread
    
    def save_thread(self, thread: Thread) -> Thread:
        """Save a thread to GraphState."""
        threads = self._state.get(Channel.THREADS, {})
        threads[thread.thread_id] = thread.model_dump()
        self._state[Channel.THREADS] = threads
        
        # Ensure workspace exists
        workspaces = self._state.get(Channel.WORKSPACES, {})
        if thread.thread_id not in workspaces:
            workspace = Workspace.create(thread.thread_id)
            workspaces[thread.thread_id] = workspace.model_dump()
            self._state[Channel.WORKSPACES] = workspaces
        
        return thread
    
    def save_threads(self, threads: List[Thread]) -> List[Thread]:
        """Save multiple threads to GraphState."""
        for thread in threads:
            self.save_thread(thread)
        return threads
    
    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get a thread by ID from state."""
        threads = self._state.get(Channel.THREADS, {})
        thread_data = threads.get(thread_id)
        
        if thread_data:
            return Thread(**thread_data)
        return None
    
    def update_thread(self, thread: Thread) -> Thread:
        """Update a thread in state."""
        threads = self._state.get(Channel.THREADS, {})
        threads[thread.thread_id] = thread.model_dump()
        self._state[Channel.THREADS] = threads
        return thread
    
    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread and its workspace from state."""
        threads = self._state.get(Channel.THREADS, {})
        
        if thread_id not in threads:
            return False
        
        # Remove from parent's children if applicable
        thread_data = threads[thread_id]
        parent_id = thread_data.get('parent_thread_id')
        
        if parent_id and parent_id in threads:
            parent_data = threads[parent_id]
            if 'child_thread_ids' in parent_data and thread_id in parent_data['child_thread_ids']:
                parent_data['child_thread_ids'].remove(thread_id)
        
        # Delete thread
        del threads[thread_id]
        self._state[Channel.THREADS] = threads
        
        # Delete workspace
        workspaces = self._state.get(Channel.WORKSPACES, {})
        if thread_id in workspaces:
            del workspaces[thread_id]
            self._state[Channel.WORKSPACES] = workspaces
        
        return True
    
    def list_threads(self) -> List[Thread]:
        """List all threads from state."""
        threads = self._state.get(Channel.THREADS, {})
        return [Thread(**thread_data) for thread_data in threads.values()]
    
    def list_active_threads(self) -> List[Thread]:
        """List all active threads from state."""
        threads = self._state.get(Channel.THREADS, {})
        return [Thread(**thread_data) for thread_data in threads.values() 
                if thread_data.get('status') == ThreadStatus.ACTIVE]
    
    def get_child_threads(self, parent_thread_id: str) -> List[Thread]:
        """Get all child threads of a parent from state."""
        parent_thread = self.get_thread(parent_thread_id)
        if not parent_thread:
            return []
        
        threads = self._state.get(Channel.THREADS, {})
        return [Thread(**threads[child_id]) for child_id in parent_thread.child_thread_ids 
                if child_id in threads]
    
    # ========== WORKSPACE MANAGEMENT ==========
    
    def get_workspace(self, thread_id: str) -> Workspace:
        """
        Get workspace for a thread from state.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            Workspace instance (creates if doesn't exist)
        """
        workspaces = self._state.get(Channel.WORKSPACES, {})
        
        if thread_id not in workspaces:
            # Create new workspace
            workspace = Workspace.create(thread_id)
            workspaces[thread_id] = workspace.model_dump()
            self._state[Channel.WORKSPACES] = workspaces
            return workspace
        
        return Workspace(**workspaces[thread_id])
    
    def update_workspace(self, workspace: Workspace) -> Workspace:
        """Update a workspace in state."""
        workspaces = self._state.get(Channel.WORKSPACES, {})
        workspaces[workspace.thread_id] = workspace.model_dump()
        self._state[Channel.WORKSPACES] = workspaces
        return workspace
    
    # ========== CONTEXT OPERATIONS ==========
    
    def add_result(self, thread_id: str, result: AgentResult) -> None:
        """Add a result to the thread's workspace."""
        workspace = self.get_workspace(thread_id)
        workspace.add_result(result)
        self.update_workspace(workspace)
    
    def add_fact(self, thread_id: str, fact: str) -> None:
        """Add a fact to the thread's workspace."""
        workspace = self.get_workspace(thread_id)
        workspace.add_fact(fact)
        self.update_workspace(workspace)
    
    def set_variable(self, thread_id: str, key: str, value: Any) -> None:
        """Set a variable in the thread's workspace."""
        workspace = self.get_workspace(thread_id)
        workspace.set_variable(key, value)
        self.update_workspace(workspace)
    
    def get_variable(self, thread_id: str, key: str, default: Any = None) -> Any:
        """Get a variable from the thread's workspace."""
        workspace = self.get_workspace(thread_id)
        return workspace.get_variable(key, default)
    
    def add_artifact(self, thread_id: str, name: str, artifact_type: str, 
                     location: str, created_by: str, 
                     metadata: Dict[str, Any] = None) -> None:
        """Add an artifact to the thread's workspace."""
        workspace = self.get_workspace(thread_id)
        workspace.add_artifact(name, artifact_type, location, created_by, metadata)
        self.update_workspace(workspace)
    
    def get_context(self, thread_id: str) -> Dict[str, Any]:
        """
        Get complete context for a thread from state.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            Dictionary containing thread info and workspace data
        """
        thread = self.get_thread(thread_id)
        workspace = self.get_workspace(thread_id)
        
        if not thread:
            return {"error": f"Thread {thread_id} not found"}

        
        return {
            "thread": thread.model_dump(),
            "workspace": workspace.model_dump(),
            "summary": workspace.get_context_summary()
        }
    
    def get_workspace_context(self, thread_id: str) -> 'WorkspaceContext':
        """
        Get workspace context for a thread from state.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            WorkspaceContext model containing all workspace data
        """
        workspace = self.get_workspace(thread_id)
        return workspace.context
    
    # ========== PARTICIPANT MANAGEMENT ==========
    
    def add_participant(self, thread_id: str, participant_id: str) -> bool:
        """Add a participant to a thread."""
        thread = self.get_thread(thread_id)
        if thread:
            thread.add_participant(participant_id)
            self.update_thread(thread)
            return True
        return False
    
    def remove_participant(self, thread_id: str, participant_id: str) -> bool:
        """Remove a participant from a thread."""
        thread = self.get_thread(thread_id)
        if thread:
            thread.remove_participant(participant_id)
            self.update_thread(thread)
            return True
        return False
    
    # ========== THREAD LIFECYCLE ==========
    
    def complete_thread(self, thread_id: str) -> bool:
        """Mark a thread as completed."""
        thread = self.get_thread(thread_id)
        if thread:
            thread.complete()
            self.update_thread(thread)
            return True
        return False
    
    def fail_thread(self, thread_id: str) -> bool:
        """Mark a thread as failed."""
        thread = self.get_thread(thread_id)
        if thread:
            thread.fail()
            self.update_thread(thread)
            return True
        return False
    
    def pause_thread(self, thread_id: str) -> bool:
        """Pause a thread."""
        thread = self.get_thread(thread_id)
        if thread:
            thread.pause()
            self.update_thread(thread)
            return True
        return False
    
    def resume_thread(self, thread_id: str) -> bool:
        """Resume a paused thread."""
        thread = self.get_thread(thread_id)
        if thread:
            thread.resume()
            self.update_thread(thread)
            return True
        return False
    
    def get_threads_by_parent(self, parent_thread_id: Optional[str] = None) -> List[Thread]:
        """
        Get threads by parent ID.
        
        Args:
            parent_thread_id: Parent thread ID, or None for root threads
            
        Returns:
            List of Thread instances with the specified parent
        """
        threads = self._state.get(Channel.THREADS, {})
        
        if parent_thread_id is None:
            # Return root threads (no parent)
            return [Thread(**thread_data) for thread_data in threads.values() 
                    if thread_data.get('parent_thread_id') is None]
        else:
            # Return threads with specified parent
            return [Thread(**thread_data) for thread_data in threads.values() 
                    if thread_data.get('parent_thread_id') == parent_thread_id]
    
    # ========== UTILITY METHODS ==========
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics from state."""
        threads = self._state.get(Channel.THREADS, {})
        workspaces = self._state.get(Channel.WORKSPACES, {})
        
        active_count = sum(1 for t in threads.values() 
                          if t.get('status') == ThreadStatus.ACTIVE)
        completed_count = sum(1 for t in threads.values() 
                             if t.get('status') == ThreadStatus.COMPLETED)
        failed_count = sum(1 for t in threads.values() 
                          if t.get('status') == ThreadStatus.FAILED)
        paused_count = sum(1 for t in threads.values() 
                          if t.get('status') == ThreadStatus.PAUSED)
        
        return {
            "threads": {
                "total": len(threads),
                "active": active_count,
                "completed": completed_count,
                "failed": failed_count,
                "paused": paused_count
            },
            "workspaces": {
                "total": len(workspaces)
            }
        }
    
    def clear_all(self) -> None:
        """
        Clear all threads and workspaces from state.
        
        Warning: This will delete all workload data.
        """
        # Clear all threads
        self._state[Channel.THREADS] = {}
        
        # Clear all workspaces
        self._state[Channel.WORKSPACES] = {}
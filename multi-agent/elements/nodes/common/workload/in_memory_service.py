"""
InMemoryWorkloadService for managing threads and workspaces.

Clean, SOLID service implementation for orchestrating thread lifecycle
and workspace operations. Provides centralized in-memory management layer.
"""

from typing import Dict, Any, Optional, List
from .interfaces import IWorkloadService
from .thread import Thread, ThreadStatus
from .workspace import Workspace
from .models import AgentResult


class InMemoryWorkloadService(IWorkloadService):
    """
    In-memory implementation of IWorkloadService.
    
    Provides centralized management for thread lifecycle and workspace operations.
    Uses in-memory dictionaries for storage - suitable for single-process applications.
    """
    
    def __init__(self):
        """Initialize the workload service with in-memory storage."""
        self._threads: Dict[str, Thread] = {}
        self._workspaces: Dict[str, Workspace] = {}
    
    # ========== THREAD PERSISTENCE ==========
    
    def create_thread(self, title: str, objective: str, initiator: str) -> Thread:
        """
        Create and save a new thread.
        
        SOLID SRP: Service only handles persistence.
        For child threads, use: parent_thread.create_child() then service.save_thread()
        """
        # Create thread
        thread = Thread.create(title, objective, initiator)
        
        # Save thread
        self._threads[thread.thread_id] = thread
        
        # Create associated workspace
        workspace = Workspace.create(thread.thread_id)
        self._workspaces[thread.thread_id] = workspace
        
        return thread
    
    def save_thread(self, thread: Thread) -> Thread:
        """
        Save a thread to storage.
        
        SOLID SRP: Service focuses on persistence only.
        Thread hierarchy is managed by Thread objects themselves.
        """
        self._threads[thread.thread_id] = thread
        
        # Ensure workspace exists
        if thread.thread_id not in self._workspaces:
            workspace = Workspace.create(thread.thread_id)
            self._workspaces[thread.thread_id] = workspace
        
        return thread
    
    def save_threads(self, threads: List[Thread]) -> List[Thread]:
        """
        Save multiple threads to storage (bulk operation).
        """
        for thread in threads:
            self.save_thread(thread)
        return threads
    
    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get a thread by ID."""
        return self._threads.get(thread_id)
    
    
    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread and its workspace."""
        if thread_id in self._threads:
            # Remove from parent's children if applicable
            thread = self._threads[thread_id]
            if thread.parent_thread_id and thread.parent_thread_id in self._threads:
                parent = self._threads[thread.parent_thread_id]
                if thread_id in parent.child_thread_ids:
                    parent.child_thread_ids.remove(thread_id)
            
            # Delete thread and workspace
            del self._threads[thread_id]
            if thread_id in self._workspaces:
                del self._workspaces[thread_id]
            return True
        return False
    
    def list_threads(self) -> List[Thread]:
        """List all threads."""
        return list(self._threads.values())
    
    def list_active_threads(self) -> List[Thread]:
        """List all active threads."""
        return [thread for thread in self._threads.values() 
                if thread.status == ThreadStatus.ACTIVE]
    
    def get_threads_by_parent(self, parent_thread_id: Optional[str] = None) -> List[Thread]:
        """Get threads by parent ID."""
        return [thread for thread in self._threads.values()
                if thread.parent_thread_id == parent_thread_id]
    
    # ========== WORKSPACE MANAGEMENT ==========
    
    def get_workspace(self, thread_id: str) -> Workspace:
        """
        Get workspace for a thread.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            Workspace instance (creates if doesn't exist)
        """
        if thread_id not in self._workspaces:
            self._workspaces[thread_id] = Workspace.create(thread_id)
        return self._workspaces[thread_id]
    
    def update_workspace(self, workspace: Workspace) -> Workspace:
        """Update a workspace."""
        self._workspaces[workspace.thread_id] = workspace
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
        Get complete context for a thread.
        
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
            "thread": {
                "thread_id": thread.thread_id,
                "title": thread.title,
                "objective": thread.objective,
                "status": thread.status,
                "participants": thread.participants,
                "parent_thread_id": thread.parent_thread_id,
                "child_thread_ids": thread.child_thread_ids
            },
            "workspace": {
                "facts": workspace.facts,
                "results": [result.model_dump() for result in workspace.results],
                "artifacts": {name: artifact.model_dump() for name, artifact in workspace.artifacts.items()},
                "variables": workspace.variables
            },
            "summary": workspace.get_context_summary()
        }
    
    def get_workspace_context(self, thread_id: str) -> 'WorkspaceContext':
        """
        Get workspace context for a thread.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            WorkspaceContext model containing all workspace data
        """
        workspace = self.get_workspace(thread_id)
        return workspace.context
    
    # ========== CONVENIENCE METHODS ==========
    
    def modify_thread(self, thread_id: str, modifier_func) -> Optional[Thread]:
        """
        Convenience method: get thread, modify it, save it.
        
        Args:
            thread_id: Thread ID to modify
            modifier_func: Function that takes Thread and modifies it
            
        Returns:
            Modified Thread or None if not found
        """
        thread = self.get_thread(thread_id)
        if thread:
            modifier_func(thread)
            return self.save_thread(thread)
        return None
    
    # ========== UTILITY METHODS ==========
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        active_threads = len(self.list_active_threads())
        total_threads = len(self._threads)
        total_workspaces = len(self._workspaces)
        
        return {
            "threads": {
                "total": total_threads,
                "active": active_threads,
                "completed": len([t for t in self._threads.values() 
                                if t.status == ThreadStatus.COMPLETED]),
                "failed": len([t for t in self._threads.values() 
                             if t.status == ThreadStatus.FAILED]),
                "paused": len([t for t in self._threads.values() 
                             if t.status == ThreadStatus.PAUSED])
            },
            "workspaces": {
                "total": total_workspaces
            }
        }
    
    def clear_all(self) -> None:
        """Clear all threads and workspaces."""
        self._threads.clear()
        self._workspaces.clear()
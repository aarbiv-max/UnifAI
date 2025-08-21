"""
Workload Service Interface

SOLID interface for workload management services.
Enables dependency inversion and supports multiple implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from .thread import Thread
from .workspace import Workspace
from .models import AgentResult


class IWorkloadService(ABC):
    """
    Interface for workload management services.
    
    Defines the contract for thread and workspace management.
    Implementations can be in-memory, state-bound, database-backed, etc.
    
    Follows SOLID principles:
    - Single Responsibility: Workload management only
    - Open/Closed: Extensible via new implementations
    - Liskov Substitution: All implementations are interchangeable
    - Interface Segregation: Focused on workload operations
    - Dependency Inversion: Clients depend on abstraction
    """
    
    # ========== THREAD PERSISTENCE ==========
    
    @abstractmethod
    def create_thread(self, title: str, objective: str, initiator: str) -> Thread:
        """
        Create and save a new thread.
        
        SOLID SRP: Service only handles persistence.
        For child threads, use: parent_thread.create_child() then service.save_thread()
        
        Args:
            title: Thread title
            objective: Thread objective/goal
            initiator: ID of the initiating agent
            
        Returns:
            Created and saved Thread instance
        """
        pass
    
    @abstractmethod
    def save_thread(self, thread: Thread) -> Thread:
        """
        Save a thread to storage.
        
        SOLID SRP: Service focuses on persistence only.
        Thread hierarchy is managed by Thread objects themselves.
        
        Args:
            thread: Thread instance to save
            
        Returns:
            Saved Thread instance
        """
        pass
    
    @abstractmethod
    def save_threads(self, threads: List[Thread]) -> List[Thread]:
        """
        Save multiple threads to storage (bulk operation).
        
        Args:
            threads: List of Thread instances to save
            
        Returns:
            List of saved Thread instances
        """
        pass
    
    @abstractmethod
    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """
        Get a thread by ID.
        
        Args:
            thread_id: Thread ID to retrieve
            
        Returns:
            Thread instance or None if not found
        """
        pass
    
    
    @abstractmethod
    def delete_thread(self, thread_id: str) -> bool:
        """
        Delete a thread and its workspace.
        
        Args:
            thread_id: Thread ID to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        pass
    
    @abstractmethod
    def list_threads(self) -> List[Thread]:
        """
        List all threads.
        
        Returns:
            List of all Thread instances
        """
        pass
    
    @abstractmethod
    def list_active_threads(self) -> List[Thread]:
        """
        List all active threads.
        
        Returns:
            List of active Thread instances
        """
        pass
    
    @abstractmethod
    def get_threads_by_parent(self, parent_thread_id: Optional[str] = None) -> List[Thread]:
        """
        Get threads by parent ID.
        
        Args:
            parent_thread_id: Parent thread ID, or None for root threads
            
        Returns:
            List of Thread instances with the specified parent
        """
        pass
    
    # ========== WORKSPACE MANAGEMENT ==========
    
    @abstractmethod
    def get_workspace(self, thread_id: str) -> Workspace:
        """
        Get workspace for a thread.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            Workspace instance (creates if doesn't exist)
        """
        pass
    
    @abstractmethod
    def update_workspace(self, workspace: Workspace) -> Workspace:
        """
        Update a workspace.
        
        Args:
            workspace: Workspace instance to update
            
        Returns:
            Updated Workspace instance
        """
        pass
    
    # ========== CONTEXT OPERATIONS ==========
    
    @abstractmethod
    def add_result(self, thread_id: str, result: AgentResult) -> None:
        """
        Add a result to the thread's workspace.
        
        Args:
            thread_id: Thread ID
            result: AgentResult to add
        """
        pass
    
    @abstractmethod
    def add_fact(self, thread_id: str, fact: str) -> None:
        """
        Add a fact to the thread's workspace.
        
        Args:
            thread_id: Thread ID
            fact: Fact string to add
        """
        pass
    
    @abstractmethod
    def set_variable(self, thread_id: str, key: str, value: Any) -> None:
        """
        Set a variable in the thread's workspace.
        
        Args:
            thread_id: Thread ID
            key: Variable key
            value: Variable value
        """
        pass
    
    @abstractmethod
    def get_variable(self, thread_id: str, key: str, default: Any = None) -> Any:
        """
        Get a variable from the thread's workspace.
        
        Args:
            thread_id: Thread ID
            key: Variable key
            default: Default value if not found
            
        Returns:
            Variable value or default
        """
        pass
    
    @abstractmethod
    def add_artifact(self, thread_id: str, name: str, artifact_type: str, 
                     location: str, created_by: str, 
                     metadata: Dict[str, Any] = None) -> None:
        """
        Add an artifact to the thread's workspace.
        
        Args:
            thread_id: Thread ID
            name: Artifact name
            artifact_type: Type of artifact
            location: Artifact location/path
            created_by: Creator ID
            metadata: Optional metadata dictionary
        """
        pass
    
    @abstractmethod
    def get_context(self, thread_id: str) -> Dict[str, Any]:
        """
        Get complete context for a thread.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            Dictionary containing thread info and workspace data
        """
        pass
    
    @abstractmethod
    def get_workspace_context(self, thread_id: str) -> 'WorkspaceContext':
        """
        Get workspace context for a thread.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            WorkspaceContext model containing all workspace data
        """
        pass
    
    # ========== CONVENIENCE METHODS ==========
    # Note: These are convenience methods that combine Thread operations + persistence
    # The core SOLID pattern is: get_thread() -> modify -> save_thread()
    
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
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get service statistics.
        
        Returns:
            Dictionary containing service statistics
        """
        pass
    
    @abstractmethod
    def clear_all(self) -> None:
        """
        Clear all threads and workspaces.
        
        Warning: This will delete all data.
        """
        pass
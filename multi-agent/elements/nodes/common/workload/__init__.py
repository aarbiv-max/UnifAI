"""
Workload Management Module

Core components for thread and workspace management in the engentic system.
Provides SOLID interfaces and implementations for workload orchestration.
"""

from .interfaces import IWorkloadService
from .models import AgentResult, WorkspaceContext
from .task import Task
from .thread import Thread, ThreadStatus
from .workspace import Workspace, ArtifactRef
from .agent_thread import AgentThread
from .in_memory_service import InMemoryWorkloadService
from .state_bound_service import StateBoundWorkloadService

__all__ = [
    'IWorkloadService',
    'AgentResult',
    'WorkspaceContext',
    'Task',
    'Thread',
    'ThreadStatus',
    'Workspace',
    'ArtifactRef',
    'AgentThread',
    'InMemoryWorkloadService',
    'StateBoundWorkloadService'
]
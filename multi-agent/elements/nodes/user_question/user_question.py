"""
User Question Node - Workflow Initiator

Converts user input into tasks and broadcasts to agent network.
Uses clean task-based architecture with agentic threading.
"""

from elements.nodes.common.base_node import BaseNode
from elements.nodes.common.capabilities.iem_capable import IEMCapableMixin
from elements.nodes.common.capabilities.workload_capable import WorkloadCapableMixin
from elements.nodes.common.workload import Task
from graph.state.graph_state import Channel
from graph.state.state_view import StateView
from elements.llms.common.chat.message import ChatMessage, Role
from typing import ClassVar


class UserQuestionNode(WorkloadCapableMixin, IEMCapableMixin, BaseNode):
    """
    Workflow initiator that processes user input.
    
    Enhanced workload management design:
    1. Create thread and workspace for workflow
    2. Copy conversation history to workspace
    3. Convert user input to public conversation
    4. Create agentic task with proper threading
    5. Broadcast task to all adjacent nodes to start workflows
    """

    # Channel permissions - includes workload channels
    READS: ClassVar[set[str]] = {Channel.USER_PROMPT, Channel.MESSAGES}
    WRITES: ClassVar[set[str]] = {Channel.MESSAGES}

    def __init__(self, *, name: str = "user_question", **kwargs):
        super().__init__(**kwargs)
        self.name = name
    def run(self, state: StateView) -> StateView:
        """Main execution - initiate workflow for user query."""
        prompt = state[Channel.USER_PROMPT]

        if not prompt or not prompt.strip():
            return state

        user_query = prompt.strip()

        # Create thread, workspace, and initiate workflow
        self._initiate_workflow(user_query, state)

        # Promote to public conversation
        user_message = ChatMessage(role=Role.USER, content=user_query)
        self.promote_to_messages(user_message)

        return state

    def _initiate_workflow(self, user_query: str, state: StateView) -> None:
        """
        Create thread, workspace, and broadcast task to start workflow.
        
        Enhanced workload management:
        1. Create thread for this workflow
        2. Copy conversation history to workspace
        3. Add workflow facts to workspace
        4. Create and broadcast task with thread context
        """
        # Create thread for this workflow
        thread = self.create_thread(
            title="User Query Processing",
            objective=f"Process user query: {user_query[:50]}..."
        )
        
        print(f"UserQuestion: Created thread {thread.thread_id} for workflow")
        
        # Copy current conversation to workspace
        self.copy_graphstate_messages_to_workspace(thread.thread_id)
        
        # Add workflow context to workspace
        self.add_fact_to_workspace(thread.thread_id, f"User query: {user_query}")
        self.add_fact_to_workspace(thread.thread_id, f"Initiated by: {self.uid}")
        self.set_workspace_variable(thread.thread_id, "workflow_type", "user_query_processing")
        self.set_workspace_variable(thread.thread_id, "initiator", self.uid)

        
        # Create clean, minimal task
        task = Task.create(
            content=user_query,
            should_respond=False,  # No direct response needed
            thread_id=thread.thread_id,
            created_by=self.uid
        )
        
        # Broadcast to all adjacent nodes
        packet_ids = self.broadcast_task(task)
        
        # Log workflow initiation with enhanced context
        workspace_summary = self.get_workspace_summary(thread.thread_id)
        print(f"UserQuestion: Initiated workflow {thread.thread_id}")

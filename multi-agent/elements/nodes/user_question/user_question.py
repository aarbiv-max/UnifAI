"""
User Question Node - Workflow Initiator

Converts user input into tasks and broadcasts to agent network.
Uses clean task-based architecture with agentic threading.
"""

from elements.nodes.common.base_node import BaseNode
from elements.nodes.common.capabilities.iem_capable import IEMCapableMixin
from elements.nodes.common.capabilities.workload_capable import WorkloadCapableMixin
from elements.nodes.common.workload import Task
from elements.nodes.common.workload.thread import ThreadStatus
from graph.state.graph_state import Channel
from graph.state.state_view import StateView
from elements.llms.common.chat.message import ChatMessage, MessageAttachment, Role
from attachments.service import AttachmentService
from typing import ClassVar, List, Dict, Any


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
    READS: ClassVar[set[str]] = {Channel.USER_PROMPT, Channel.MESSAGES, Channel.PROMPT_ATTACHMENTS}
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

        # Check for attachments and augment the query
        attachments_data = state.get(Channel.PROMPT_ATTACHMENTS, [])
        attachment_metas = self._build_attachment_metadata(attachments_data)
        augmented_query = self._augment_with_attachments(user_query, attachments_data)

        # Create thread, workspace, and initiate workflow
        self._initiate_workflow(augmented_query, state)

        # Promote to public conversation (store original prompt, attach metadata)
        user_message = ChatMessage(
            role=Role.USER,
            content=user_query,
            attachments=attachment_metas or None,
        )
        self.promote_to_messages(user_message)

        return state

    def _initiate_workflow(self, user_query: str, state: StateView) -> None:
        """
        Create or reuse thread, workspace, and broadcast task to start workflow.
        
        Enhanced workload management with thread reuse:
        1. Check for existing active thread by this initiator (user question node)
        2. Reuse existing thread if found (conversation continuity)
        3. Create new thread if none exists
        4. Copy conversation history to workspace
        5. Add workflow facts to workspace
        6. Create and broadcast task with thread context
        
        Thread reuse ensures:
        - Conversation continuity across multiple user inputs
        - Orchestrator can reference previous work plans
        - Context accumulates over the session
        """
        # Try to find existing active thread for this user question node
        existing_threads = self.threads.list_threads_by_initiator(self.uid)
        active_thread = None
        
        # Find most recent active root thread
        for thread in existing_threads:
            if thread.status == ThreadStatus.ACTIVE and not thread.parent_thread_id:
                # Found an active root thread initiated by this node
                active_thread = thread
                print(f"🔄 [UserQuestion] Reusing existing thread {thread.thread_id} for conversation continuity")
                break
        
        if active_thread:
            # Reuse existing thread
            thread = active_thread
        else:
            # Create new thread for this workflow
            thread = self.threads.create_root_thread(
                title="User Query Processing",
                objective=f"Process user query: {user_query[:50]}...",
                initiator=self.uid
            )
            print(f"📝 [UserQuestion] Created new thread {thread.thread_id} for workflow")
        
        # Copy current conversation to workspace using new SOLID API
        self.copy_graphstate_messages_to_workspace(thread.thread_id)
        
        # Add workflow context to workspace
        self.workspaces.add_fact(thread.thread_id, f"User query: {user_query}")
        self.workspaces.add_fact(thread.thread_id, f"Initiated by: {self.uid}")
        self.workspaces.set_variable(thread.thread_id, "workflow_type", "user_query_processing")
        self.workspaces.set_variable(thread.thread_id, "initiator", self.uid)

        
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
        if active_thread:
            print(f"🔄 [UserQuestion] Continued workflow in thread {thread.thread_id}")
        else:
            print(f"📝 [UserQuestion] Initiated new workflow {thread.thread_id}")

    @staticmethod
    def _build_attachment_metadata(
        attachments_data: List[Dict[str, Any]],
    ) -> List[MessageAttachment]:
        """Convert raw attachment dicts into MessageAttachment metadata."""
        return [
            MessageAttachment(
                filename=a["filename"],
                extension=a["extension"],
                char_count=a.get("char_count", 0),
            )
            for a in attachments_data
        ]

    @staticmethod
    def _augment_with_attachments(
        user_query: str,
        attachments_data: List[Dict[str, Any]],
    ) -> str:
        """
        If attachments are present, build an augmented prompt that includes
        extracted document text as context for the LLM.
        """
        if not attachments_data:
            return user_query

        from attachments.models import AttachmentContent

        contents = [
            AttachmentContent(
                filename=a["filename"],
                extension=a["extension"],
                text_content=a["text_content"],
                char_count=a.get("char_count", 0),
            )
            for a in attachments_data
        ]
        return AttachmentService.build_augmented_prompt(user_query, contents)


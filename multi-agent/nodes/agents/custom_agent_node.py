from typing import Optional, Any, List
from graph.state.graph_state import GraphState
from graph.step_context import StepContext
from llms.chat.message import ChatMessage, Role
from nodes.base_node import BaseNode
from nodes.mixins.llm_capable import LlmCapableMixin
from nodes.mixins.retriever_capable import RetrieverCapableMixin
from nodes.mixins.tool_capable import ToolCapableMixin


class CustomAgentNode(
    LlmCapableMixin,
    RetrieverCapableMixin,
    ToolCapableMixin,
    BaseNode
):
    """
    Orchestrates:
      1. Retrieval (if any)
      2. System message injection
      3. Pure LLM chat or LLM+tool loop
      4. Writes final output into GraphState
    """

    def __init__(
            self,
            *,
            step_ctx: StepContext,
            name: str,
            llm: Any,
            retriever: Any = None,
            tools: List[Any] = (),
            system_message: str = "",
            retries: int = 1,
            max_rounds: Optional[int] = 20,
            **kwargs: Any
    ):
        super().__init__(
            step_ctx=step_ctx,
            name=name,
            llm=llm,
            retriever=retriever,
            tools=tools,
            system_message=system_message,
            retries=retries,
            **kwargs
        )
        self.max_rounds = max_rounds

    def _prepare_messages(self, state: GraphState) -> List[ChatMessage]:
        msgs = state.get("messages", []).copy()
        if not msgs:
            raise ValueError("state['messages'] missing")

        # 1) Optionally prepend context via retriever
        msgs[-1] = self.augment_with_context(msgs[-1])

        # 2) Inject or update system message at the front
        if self.system_message:
            system = ChatMessage(role=Role.SYSTEM, content=self.system_message)
            if not msgs or msgs[0].role != Role.SYSTEM:
                msgs.insert(0, system)
            elif msgs[0].content != self.system_message:
                msgs[0] = system

        return msgs

    def run(self, state: GraphState) -> GraphState:
        # Build the initial chat history
        history = self._prepare_messages(state)

        # Pure LLM path if no tools
        if not self.tools:
            assistant = self._chat(history)
        else:
            # Bind tools into LLM if supported
            self._bind_tools(self.tools)

            # Execute the tool cycle and get the final assistant message
            assistant = self._execute_tool_cycle(
                initial_history=history,
                chat_function=self._chat,
                max_rounds=self.max_rounds
            )

        # Persist only the final assistant content
        state["nodes_output"] = {self.uid: assistant.content}
        return state

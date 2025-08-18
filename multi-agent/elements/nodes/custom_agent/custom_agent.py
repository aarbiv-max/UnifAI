from typing import Optional, Any, List
from graph.state.graph_state import Channel
from graph.state.state_view import StateView
from elements.llms.common.chat.message import ChatMessage, Role
from elements.nodes.common.base_node import BaseNode
from elements.nodes.common.capabilities.llm_capable import LlmCapableMixin
from elements.nodes.common.capabilities.retriever_capable import RetrieverCapableMixin
from elements.nodes.common.capabilities.tool_capable import ToolCapableMixin
from elements.providers.mcp_server_client.mcp_provider import McpProvider


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
    READS = {Channel.USER_PROMPT, Channel.MESSAGES}
    WRITES = {Channel.NODES_OUTPUT}

    def __init__(
            self,
            *,
            llm: Any,
            retriever: Any = None,
            tools: List[Any] = (),
            system_message: str = "",
            mcp_provider: McpProvider = None,
            retries: int = 1,
            max_rounds: Optional[int] = 15,
            **kwargs: Any
    ):
        super().__init__(
            llm=llm,
            retriever=retriever,
            tools=tools,
            system_message=system_message,
            retries=retries,
            **kwargs
        )
        self.mcp_provider = mcp_provider
        self.max_rounds = max_rounds

    def _prepare_messages(self, state: StateView) -> List[ChatMessage]:
        msgs = state.get(Channel.MESSAGES, []).copy()
        if not msgs:
            raise ValueError(F"state['{Channel.MESSAGES.value}'] missing")

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

    def run(self, state: StateView) -> StateView:
        # Build the initial chat history
        history = self._prepare_messages(state)

        if self.mcp_provider:
            # Add MCP tools to the internal tools dictionary
            for tool in self.mcp_provider.get_tools():
                self._tools[tool.name] = tool

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
        state[Channel.NODES_OUTPUT] = {self.uid: assistant.content}
        return state

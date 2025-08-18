from elements.nodes.common.base_node import BaseNode
from elements.nodes.common.capabilities.llm_capable import LlmCapableMixin
from graph.state.graph_state import Channel
from graph.state.state_view import StateView
from elements.llms.common.chat.message import ChatMessage, Role


class LLMMergerNode(LlmCapableMixin, BaseNode):
    """
    Uses an LLM to merge outputs from multiple agents.
    """
    READS = {Channel.USER_PROMPT, Channel.NODES_OUTPUT, Channel.MESSAGES}
    WRITES = {Channel.MESSAGES}

    def __init__(self,
                 *,
                 llm,
                 system_message: str = "",
                 retries: int = 1,
                 **kwargs):
        super().__init__(llm=llm,
                         system_message=system_message,
                         retries=retries,
                         **kwargs)

    def run(self, state: StateView) -> StateView:
        messages: list[ChatMessage] = state.get(Channel.MESSAGES, []).copy()

        if self.system_message:
            messages.insert(0, ChatMessage(role=Role.SYSTEM,
                                           content=self.system_message))

        # collate upstream outputs
        agents_output = state.get(Channel.NODES_OUTPUT, {})
        user_q = state.get(Channel.USER_PROMPT, "")
        user_block = "\n".join(f"{k}: {v}" for k, v in agents_output.items())
        merged_prompt = f"context:\n{user_block}\n\nuser question: {user_q}"
        messages.append(ChatMessage(role=Role.USER, content=merged_prompt))

        answer = self._chat(messages)
        state[Channel.MESSAGES] = [answer]
        return state

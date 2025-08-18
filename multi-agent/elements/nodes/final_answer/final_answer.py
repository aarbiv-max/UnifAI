from typing import Sequence, Mapping
from elements.nodes.common.base_node import BaseNode
from graph.state.graph_state import Channel
from graph.state.state_view import StateView
from elements.llms.common.chat.message import ChatMessage, Role


class _DefaultFormatter:
    """Internal helper—formats nodes_output into a final reply."""

    @staticmethod
    def format(outputs: Mapping[str, str]) -> str:
        if not outputs:
            return "I apologize, but I don't have any specific information to provide."
        if len(outputs) == 1:
            return next(iter(outputs.values())).strip()

        parts = []
        for name, text in outputs.items():
            text = text.strip()
            if not text:
                continue
            display = name.replace("_", " ").title()
            parts.append(f"**{display}:**\n{text}")
        return "\n\n".join(parts) if parts else (
            "I apologize, but I don't have any specific information to provide."
        )


class FinalAnswerNode(BaseNode):
    """
    Ensures the conversation ends with an assistant response if the user spoke last.
    Uses an internal formatter class—no external injection required, but you
    can still override `_formatter` in a subclass if you want a different style.
    """
    READS = {Channel.MESSAGES, Channel.NODES_OUTPUT}
    WRITES = {Channel.MESSAGES, Channel.OUTPUT}

    # default formatter instance; you can override in a subclass if needed
    _formatter = _DefaultFormatter()

    def __init__(
            self,
            *,
            name: str = "final_answer",
            **kwargs
    ):
        super().__init__(**kwargs)
        self.name = name

    def run(self, state: StateView) -> StateView:
        messages = state.get(Channel.MESSAGES, [])

        if not self._last_is_assistant(messages):
            raw = state.get(Channel.NODES_OUTPUT, {})
            reply = self._formatter.format(raw)
            self._append_message(state, reply)

        messages = state.get(Channel.MESSAGES, [])
        if messages:
            state[Channel.OUTPUT] = messages[-1].content

        return state

    @staticmethod
    def _last_is_assistant(messages: Sequence[ChatMessage]) -> bool:
        return bool(messages) and messages[-1].role == Role.ASSISTANT

    def _append_message(self, state: StateView, content: str) -> None:
        new_msg = ChatMessage(role=Role.ASSISTANT, content=content)
        updated = list(state.get(Channel.MESSAGES, [])) + [new_msg]
        state[Channel.MESSAGES] = updated

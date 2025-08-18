from elements.nodes.common.base_node import BaseNode
from graph.state.graph_state import Channel
from graph.state.state_view import StateView
from elements.llms.common.chat.message import ChatMessage, Role


class UserQuestionNode(BaseNode):
    """
    Injects the raw user prompt into the chat history.
    """
    READS = {Channel.USER_PROMPT}
    WRITES = {Channel.MESSAGES}

    def __init__(self,
                 *,
                 name: str = "user_question",
                 **kwargs):
        super().__init__(**kwargs)
        self.name = name

    def run(self, state: StateView) -> StateView:
        prompt = state[Channel.USER_PROMPT]
        state[Channel.MESSAGES] = [ChatMessage(role=Role.USER, content=prompt)]
        return state

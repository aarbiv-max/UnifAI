from typing import Literal
from .identifiers import Identifier
from elements.nodes.common.base_config import NodeBaseConfig
from pydantic import Field


class UserQuestionNodeConfig(NodeBaseConfig):
    """
    Logs or passes through user input without modification.
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE

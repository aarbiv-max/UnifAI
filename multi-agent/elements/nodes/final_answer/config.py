from typing import Literal
from .identifiers import Identifier
from elements.nodes.common.base_config import NodeBaseConfig


class FinalAnswerNodeConfig(NodeBaseConfig):
    """
    Emits the final aggregated answer without overrides.
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE

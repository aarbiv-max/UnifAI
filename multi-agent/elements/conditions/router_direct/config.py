from typing import Literal
from elements.conditions.common.base_config import BaseConditionConfig
from .identifiers import Identifier


class RouterDirectConditionConfig(BaseConditionConfig):
    """
    Configuration for IEM-based router condition.
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE
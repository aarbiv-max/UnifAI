from typing import ClassVar
from elements.common.base_element_spec import BaseElementSpec
from core.enums import ResourceCategory
from ..config import FinalAnswerNodeConfig
from ..final_answer_node_factory import FinalAnswerNodeFactory
from ..final_answer import FinalAnswerNode
from ..identifiers import Identifier, META


class FinalAnswerNodeElementSpec(BaseElementSpec):
    """Element specification for Final Answer Node."""

    category: ClassVar[ResourceCategory] = ResourceCategory.NODE
    type_key = Identifier.TYPE
    name = META.name
    description = META.description
    config_schema = FinalAnswerNodeConfig
    factory_cls = FinalAnswerNodeFactory
    reads = FinalAnswerNode.READS
    writes = FinalAnswerNode.WRITES
    tags = META.tags

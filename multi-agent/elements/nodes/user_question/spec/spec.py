from elements.common.base_element_spec import BaseElementSpec
from core.enums import ResourceCategory
from ..config import UserQuestionNodeConfig
from ..user_question_node_factory import UserQuestionNodeFactory
from ..user_question import UserQuestionNode
from ..identifiers import Identifier, META


class UserQuestionNodeElementSpec(BaseElementSpec):
    """Element specification for User Question Node."""

    category = ResourceCategory.NODE
    type_key = Identifier.TYPE
    name = META.name
    description = META.description
    config_schema = UserQuestionNodeConfig
    factory_cls = UserQuestionNodeFactory
    reads = UserQuestionNode.READS
    writes = UserQuestionNode.WRITES
    tags = META.tags

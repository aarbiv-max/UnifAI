from elements.common.base_element_spec import BaseElementSpec
from core.enums import ResourceCategory
from ..config import CustomAgentNodeConfig
from ..custom_agent import CustomAgentNode
from ..custom_agent_node_factory import CustomAgentNodeFactory
from ..identifiers import Identifier, META


class CustomAgentNodeElementSpec(BaseElementSpec):
    """Element specification for Custom Agent Node."""

    category = ResourceCategory.NODE
    type_key = Identifier.TYPE
    name = META.name
    description = META.description
    config_schema = CustomAgentNodeConfig
    factory_cls = CustomAgentNodeFactory
    reads = CustomAgentNode.READS
    writes = CustomAgentNode.WRITES
    tags = META.tags

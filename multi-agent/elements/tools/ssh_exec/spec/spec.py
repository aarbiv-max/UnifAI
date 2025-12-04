from elements.common.base_element_spec import BaseElementSpec
from elements.tools.common.card_builder import ToolCardBuilder
from core.enums import ResourceCategory
from ..config import SshExecToolConfig
from ..ssh_exec_factory import SshExecToolFactory
from ..identifiers import Identifier, META


class SshExecToolElementSpec(BaseElementSpec):
    """Element specification for SSH Exec Tool."""

    category = ResourceCategory.TOOL
    type_key = Identifier.TYPE
    name = META.name
    description = META.description
    config_schema = SshExecToolConfig
    factory_cls = SshExecToolFactory
    card_builder_cls = ToolCardBuilder
    tags = META.tags

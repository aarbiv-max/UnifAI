from mas.core.enums import ResourceCategory
from mas.elements.common.base_element_spec import BaseElementSpec
from ..config import SandboxExecToolConfig
from ..identifiers import META, Identifier
from ..sandbox_exec_factory import SandboxExecToolFactory
from ..validator import SandboxExecToolValidator


class SandboxExecToolElementSpec(BaseElementSpec):
    """Element specification for the Sandbox Exec tool."""

    category = ResourceCategory.TOOL
    type_key = Identifier.TYPE
    name = META.name
    description = META.description
    config_schema = SandboxExecToolConfig
    factory_cls = SandboxExecToolFactory
    tags = META.tags
    validator_cls = SandboxExecToolValidator

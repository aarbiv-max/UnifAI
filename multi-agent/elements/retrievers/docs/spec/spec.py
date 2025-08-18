from elements.common.base_element_spec import BaseElementSpec
from core.enums import ResourceCategory
from ..config import DocsRetrieverConfig
from ..docs_retriever_factory import DocsRetrieverFactory
from ..identifiers import Identifier, META

class DocsRetrieverElementSpec(BaseElementSpec):
    """Element specification for Docs Retriever."""

    category = ResourceCategory.RETRIEVER
    type_key = Identifier.TYPE
    name = META.name
    description = META.description
    config_schema = DocsRetrieverConfig
    factory_cls = DocsRetrieverFactory
    tags = META.tags
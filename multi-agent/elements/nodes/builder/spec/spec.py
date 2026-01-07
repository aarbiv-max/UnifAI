"""
Element specification for Builder Agent Node.

Registers the builder node with the ElementRegistry for auto-discovery.
"""

from elements.common.base_element_spec import BaseElementSpec
from core.enums import ResourceCategory
from elements.nodes.builder.config import BuilderNodeConfig
from elements.nodes.builder.builder_node import BuilderNode
from elements.nodes.builder.builder_node_factory import BuilderNodeFactory
from elements.nodes.builder.identifiers import Identifier, META
from elements.nodes.builder.validator import BuilderNodeValidator


class BuilderNodeElementSpec(BaseElementSpec):
    """Element specification for Builder Agent Node."""

    category = ResourceCategory.NODE
    type_key = Identifier.TYPE
    name = META.name
    description = META.description
    config_schema = BuilderNodeConfig
    factory_cls = BuilderNodeFactory
    reads = BuilderNode.total_reads()
    writes = BuilderNode.total_writes()
    tags = META.tags
    validator_cls = BuilderNodeValidator


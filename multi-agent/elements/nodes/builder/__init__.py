"""
Builder Agent Node.

A multi-phase agent that creates workflows based on user requests.
Works in 4 phases: Analyze, Search Resources, Design Workflow, Validate.

Note: Heavy imports (BuilderNode, BuilderNodeFactory) are deferred to avoid
circular imports when this module is loaded during type resolution.
"""

# Light imports that don't cause circular dependencies
from .config import BuilderNodeConfig
from .identifiers import Identifier, META, BuilderPhase

# Lazy imports for heavy dependencies
def _get_builder_node():
    from .builder_node import BuilderNode
    return BuilderNode

def _get_builder_node_factory():
    from .builder_node_factory import BuilderNodeFactory
    return BuilderNodeFactory

def _get_builder_node_validator():
    from .validator import BuilderNodeValidator
    return BuilderNodeValidator

__all__ = [
    "BuilderNodeConfig",
    "BuilderPhase",
    "Identifier",
    "META",
    # These are available via lazy loading
    "_get_builder_node",
    "_get_builder_node_factory", 
    "_get_builder_node_validator",
]


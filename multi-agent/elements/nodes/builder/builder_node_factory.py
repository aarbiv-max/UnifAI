"""
Factory for creating BuilderNode instances.

Injects the required services for the builder agent to function.
"""

from elements.common.base_factory import BaseFactory
from elements.common.exceptions import PluginConfigurationError
from .config import BuilderNodeConfig
from .builder_node import BuilderNode
from .identifiers import Identifier


class BuilderNodeFactory(BaseFactory[BuilderNodeConfig, BuilderNode]):
    """
    Factory for creating BuilderNode instances.
    
    Injects the services needed for workflow building:
    - resources_service: For searching user resources
    - blueprint_service: For saving blueprints
    - catalog_service: For element catalog access
    - validation_service: For blueprint validation
    """

    def accepts(self, cfg: BuilderNodeConfig, element_type: str) -> bool:
        return element_type == Identifier.TYPE

    def create(self, cfg: BuilderNodeConfig, **deps) -> BuilderNode:
        """
        Create a BuilderNode with all required dependencies.
        
        Args:
            cfg: BuilderNodeConfig with configuration
            **deps: Dependencies including:
                - llm: The language model instance
                - resources_service: ResourcesService
                - blueprint_service: BlueprintService
                - catalog_service: CatalogService
                - validation_service: ElementValidationService
                
        Returns:
            Configured BuilderNode instance
        """
        try:
            return BuilderNode(
                llm=deps.pop("llm"),
                resources_service=deps.pop("resources_service", None),
                blueprint_service=deps.pop("blueprint_service", None),
                catalog_service=deps.pop("catalog_service", None),
                validation_service=deps.pop("validation_service", None),
                system_message=cfg.system_message,
                max_rounds=cfg.max_rounds,
                retries=cfg.retries,
            )
        except Exception as e:
            raise PluginConfigurationError(
                f"BuilderNodeFactory.create failed: {e}",
                cfg.model_dump()
            ) from e


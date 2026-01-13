"""
Protocol definitions for Builder Node services.

Defines interfaces for the services used by the Builder Agent.
Uses Protocol for structural subtyping to avoid tight coupling.
"""

from typing import Protocol, Any, Dict, List, Optional, Tuple, runtime_checkable


@runtime_checkable
class ResourcesServiceProtocol(Protocol):
    """Protocol for the resources service used to find and create resources."""
    
    def find_resources(
        self,
        user_id: str,
        category: Optional[str] = None,
        type: Optional[str] = None,
        **kwargs: Any
    ) -> Tuple[List[Any], int]:
        """
        Find resources matching the criteria.
        
        Args:
            user_id: User ID to search for
            category: Optional category filter
            type: Optional type filter
            
        Returns:
            Tuple of (list of resources, total count)
        """
        ...
    
    def create(
        self,
        user_id: str,
        category: str,
        type: str,
        name: str,
        config: Dict[str, Any],
        **kwargs: Any
    ) -> Any:
        """
        Create a new resource.
        
        Args:
            user_id: User ID
            category: Resource category
            type: Resource type
            name: Resource name
            config: Resource configuration
            
        Returns:
            Created resource document
        """
        ...


@runtime_checkable
class BlueprintServiceProtocol(Protocol):
    """Protocol for the blueprint service used to save and validate blueprints."""
    
    def validate_draft(
        self,
        draft_dict: Dict[str, Any],
        timeout_seconds: float = 10.0,
    ) -> Any:
        """
        Validate a blueprint draft.
        
        Args:
            draft_dict: Blueprint draft dictionary to validate
            timeout_seconds: Timeout for validation checks
            
        Returns:
            BlueprintValidationResult with validation status
        """
        ...
    
    def save_draft(
        self,
        *,
        user_id: str,
        draft_dict: Dict[str, Any],
    ) -> str:
        """
        Save a blueprint draft.
        
        Args:
            user_id: User ID (keyword-only)
            draft_dict: Blueprint draft dictionary to save
            
        Returns:
            Blueprint ID
        """
        ...


@runtime_checkable
class CatalogServiceProtocol(Protocol):
    """Protocol for the catalog service used to access element definitions."""
    
    def get_element_spec(
        self,
        category: str,
        type_key: str
    ) -> Optional[Any]:
        """
        Get element specification.
        
        Args:
            category: Element category
            type_key: Element type key
            
        Returns:
            Element spec or None
        """
        ...
    
    def list_elements(
        self,
        category: Optional[str] = None
    ) -> List[Any]:
        """
        List available elements.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of element specs
        """
        ...


@runtime_checkable
class ValidationServiceProtocol(Protocol):
    """Protocol for the validation service."""
    
    def validate(
        self,
        config: Any,
        **kwargs: Any
    ) -> Any:
        """
        Validate a configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Validation result
        """
        ...


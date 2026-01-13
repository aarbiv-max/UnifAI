"""
Agent Inventory Registry for Builder Tools.

Centralized registry for agent inventory implementations.
Follows the codebase's Singleton + Registry pattern.
"""

import threading
from typing import Any, Dict, List, Optional, Type

from global_utils.utils.singleton import SingletonMeta
from .agent_inventory import (
    AgentInventory,
    AgentInfo,
    InventoryType,
    CustomAgentInventory,
    A2AAgentInventory,
    ResourcesServiceProtocol,
)


class InventoryRegistry(metaclass=SingletonMeta):
    """
    Registry for agent inventory implementations.
    
    Uses Singleton pattern for global access.
    Thread-safe with RLock for concurrent access.
    
    Usage:
        registry = InventoryRegistry()
        registry.register(CustomAgentInventory())
        results = registry.search(resources_service, user_id)
    """
    
    _lock = threading.RLock()
    
    def __init__(self) -> None:
        self._inventories: Dict[InventoryType, AgentInventory] = {}
    
    # ---------- Registration ----------
    
    def register(self, inventory: AgentInventory) -> None:
        """
        Register an inventory implementation.
        
        Args:
            inventory: AgentInventory instance to register
            
        Raises:
            ValueError: If inventory type already registered
        """
        with self._lock:
            inv_type = inventory.inventory_type
            if inv_type in self._inventories:
                raise ValueError(f"Inventory already registered: {inv_type}")
            self._inventories[inv_type] = inventory
    
    def register_if_absent(self, inventory: AgentInventory) -> None:
        """Register inventory only if not already registered."""
        with self._lock:
            if inventory.inventory_type not in self._inventories:
                self._inventories[inventory.inventory_type] = inventory
    
    # ---------- Access ----------
    
    def get(self, inv_type: InventoryType) -> Optional[AgentInventory]:
        """Get inventory by type."""
        return self._inventories.get(inv_type)
    
    def has(self, inv_type: InventoryType) -> bool:
        """Check if inventory type is registered."""
        return inv_type in self._inventories
    
    def list_types(self) -> List[InventoryType]:
        """List all registered inventory types."""
        return list(self._inventories.keys())
    
    # ---------- Search ----------
    
    def search(
        self,
        resources_service: ResourcesServiceProtocol,
        user_id: str,
        inventories: Optional[List[InventoryType]] = None,
        capability_filter: Optional[List[str]] = None,
        provider_list: Optional[List[Dict[str, Any]]] = None,
        limit: int = 50,
    ) -> Dict[InventoryType, List[AgentInfo]]:
        """
        Search across multiple inventories.
        
        Args:
            resources_service: Service for accessing resources
            user_id: User ID for filtering
            inventories: Specific inventory types to search (None = all)
            capability_filter: Optional required capabilities
            provider_list: Optional provider configs for matching
            limit: Maximum results per inventory
            
        Returns:
            Dict mapping inventory type to list of AgentInfo
        """
        types_to_search = inventories or list(self._inventories.keys())
        
        results: Dict[InventoryType, List[AgentInfo]] = {}
        for inv_type in types_to_search:
            if inv_type not in self._inventories:
                continue
            
            inventory = self._inventories[inv_type]
            agents = inventory.search(
                resources_service=resources_service,
                user_id=user_id,
                capability_filter=capability_filter,
                provider_list=provider_list,
                limit=limit,
            )
            results[inv_type] = agents
        
        return results
    
    def search_all(
        self,
        resources_service: ResourcesServiceProtocol,
        user_id: str,
        capability_filter: Optional[List[str]] = None,
        provider_list: Optional[List[Dict[str, Any]]] = None,
        limit: int = 50,
    ) -> List[AgentInfo]:
        """
        Search all inventories and return flattened results.
        
        Args:
            resources_service: Service for accessing resources
            user_id: User ID for filtering
            capability_filter: Optional required capabilities
            provider_list: Optional provider configs
            limit: Maximum results per inventory
            
        Returns:
            Flattened list of AgentInfo from all inventories
        """
        results = self.search(
            resources_service=resources_service,
            user_id=user_id,
            inventories=None,
            capability_filter=capability_filter,
            provider_list=provider_list,
            limit=limit,
        )
        
        all_agents: List[AgentInfo] = []
        for agents in results.values():
            all_agents.extend(agents)
        
        return all_agents
    
    # ---------- Utilities ----------
    
    def parse_inventory_types(
        self,
        type_strings: Optional[List[str]]
    ) -> Optional[List[InventoryType]]:
        """
        Parse inventory type strings to enum values.
        
        Args:
            type_strings: List of type strings (e.g., ['custom_agents', 'a2a_agents'])
                         None means all inventories.
                         
        Returns:
            List of InventoryType enums, or None for all.
        """
        if not type_strings:
            return None
        
        result = []
        for type_str in type_strings:
            try:
                result.append(InventoryType(type_str))
            except ValueError:
                continue  # Skip invalid types
        
        return result if result else None
    
    # ---------- Statistics ----------
    
    def get_stats(self) -> Dict[str, int]:
        """Get registry statistics."""
        return {"inventory_count": len(self._inventories)}


# ---------------------------------------------------------------------------
# Module-level singleton instance with default inventories
# ---------------------------------------------------------------------------

def get_inventory_registry() -> InventoryRegistry:
    """
    Get the global inventory registry instance.
    
    Registers default inventories on first access.
    """
    registry = InventoryRegistry()
    
    # Register default inventories
    registry.register_if_absent(CustomAgentInventory())
    registry.register_if_absent(A2AAgentInventory())
    
    return registry


# Convenience alias
inventory_registry = get_inventory_registry()

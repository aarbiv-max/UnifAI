"""
Element Card Service - orchestrates card building.

Builds element cards in dependency order, passing dependency cards
to parent element builders.

Example:
    Given a BlueprintSpec with:
    - CustomAgentNode (references: MCP Provider, Slack Tool, Retriever)
    - MCP Provider (has tool_names: ["git_status", "file_read"])
    - Slack Tool
    - Retriever
    
    The service:
    1. Builds dependency graph: CustomAgent depends on [MCP, Slack, Retriever]
    2. Sorts: [MCP, Slack, Retriever, CustomAgent] (leaves first)
    3. Builds MCP card → skills: [git_status, file_read]
    4. Builds Slack card → skills: [Slack Messenger]
    5. Builds Retriever card → capabilities: [docs_retrieval]
    6. Builds CustomAgent card with dependency_cards = {mcp, slack, retriever}
       → Composes: skills: [git_status, file_read, Slack Messenger]
                   capabilities: [docs_retrieval]
"""

from typing import Dict, List, Tuple, Any
from collections import defaultdict
from core.enums import ResourceCategory
from core.ref.models import Ref
from elements.common.card.models import ElementCard, CardBuildInput, SpecMetadata
from elements.common.card.default import DefaultCardBuilder
from catalog.element_registry import ElementRegistry


class ElementCardService:
    """
    Builds ElementCards in dependency order.
    
    This service is the central orchestrator for card building.
    It ensures that when building a card for an element that references
    other elements, those dependency cards are already built and available.
    """
    
    def __init__(self, element_registry: ElementRegistry):
        self._registry = element_registry
    
    def build_all_cards(
        self,
        configs: Dict[str, Tuple[ResourceCategory, str, str, Any]]
    ) -> Dict[str, ElementCard]:
        """
        Build cards for all configs in dependency order.
        
        This is the main entry point for building cards from a BlueprintSpec
        or a collection of resources.
        
        Args:
            configs: Dictionary mapping resource ID to a tuple of:
                     (category, user_name, type_key, config_model)
                     
                     Example:
                     {
                         "node-123": (NODE, "My Agent", "custom_agent", CustomAgentNodeConfig(...)),
                         "mcp-456": (PROVIDER, "MCP Server", "mcp_provider", McpProviderConfig(...)),
                         "tool-789": (TOOL, "Slack", "slack_tool", SlackToolConfig(...)),
                     }
        
        Returns:
            Dictionary mapping resource ID to built ElementCard.
        """
        deps = self._build_dependency_graph(configs)
        order = self._topological_sort(list(configs.keys()), deps)
        
        cards: Dict[str, ElementCard] = {}
        
        for rid in order:
            category, name, type_key, config = configs[rid]
            
            dep_cards = {
                dep_rid: cards[dep_rid]
                for dep_rid in deps.get(rid, [])
                if dep_rid in cards
            }
            
            card = self._build_single_card(
                category, rid, name, type_key, config, dep_cards
            )
            cards[rid] = card
        
        return cards
    
    def build_single_card(
        self,
        category: ResourceCategory,
        rid: str,
        name: str,
        type_key: str,
        config: Any,
        dependency_cards: Dict[str, ElementCard] = None
    ) -> ElementCard:
        """
        Build a single element card.
        
        Use this when:
        - Building a card for a leaf element (no dependencies)
        - Dependency cards are already available
        - Building a card for a single resource
        """
        return self._build_single_card(
            category, rid, name, type_key, config, 
            dependency_cards or {}
        )
    
    def _build_single_card(
        self,
        category: ResourceCategory,
        rid: str,
        name: str,
        type_key: str,
        config: Any,
        dependency_cards: Dict[str, ElementCard]
    ) -> ElementCard:
        """Internal: Build a single card with dependency cards."""
        spec = self._registry.get_spec(category, type_key)
        
        spec_metadata = SpecMetadata(
            category=spec.category,
            type_key=spec.type_key,
            name=spec.name,
            description=spec.description,
            capability_names=list(getattr(spec, 'capability_names', []))
        )
        
        build_input = CardBuildInput(
            rid=rid,
            name=name,
            config=config,
            spec_metadata=spec_metadata,
            dependency_cards=dependency_cards
        )
        
        builder_cls = getattr(spec, 'card_builder_cls', DefaultCardBuilder)
        builder = builder_cls()
        
        return builder.build(build_input)
    
    def _build_dependency_graph(
        self,
        configs: Dict[str, Tuple[ResourceCategory, str, str, Any]]
    ) -> Dict[str, List[str]]:
        """Find refs in each config to build dependency graph."""
        deps: Dict[str, List[str]] = defaultdict(list)
        config_rids = set(configs.keys())
        
        for rid, (category, name, type_key, config) in configs.items():
            dep_rids = self._find_refs_in_config(config)
            for dep_rid in dep_rids:
                if dep_rid in config_rids:
                    deps[rid].append(dep_rid)
        
        return dict(deps)
    
    def _find_refs_in_config(self, config: Any) -> List[str]:
        """Walk config fields to find all Refs."""
        refs: List[str] = []
        
        for field_name, field_value in config.__dict__.items():
            if isinstance(field_value, Ref):
                refs.append(field_value.ref)
            elif isinstance(field_value, list):
                for item in field_value:
                    if isinstance(item, Ref):
                        refs.append(item.ref)
        
        return refs
    
    def _topological_sort(
        self,
        rids: List[str],
        deps: Dict[str, List[str]]
    ) -> List[str]:
        """Sort rids so dependencies come before dependents."""
        visited: set = set()
        order: List[str] = []
        
        def visit(rid: str):
            if rid in visited:
                return
            visited.add(rid)
            for dep_rid in deps.get(rid, []):
                visit(dep_rid)
            order.append(rid)
        
        for rid in rids:
            visit(rid)
        
        return order


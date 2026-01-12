"""
Element Card Service - orchestrates card building.

Builds element cards in dependency order, passing dependency cards
to parent element builders.

Example:
    Given elements with:
    - CustomAgentNode (references: MCP Provider, Slack Tool, Retriever)
    - MCP Provider (has tool_names: ["git_status", "file_read"])
    - Slack Tool
    - Retriever
    
    The service:
    1. Builds dependency graph from pre-computed dependency_rids
    2. Sorts: [MCP, Slack, Retriever, CustomAgent] (leaves first)
    3. Builds MCP card → skills: [git_status, file_read]
    4. Builds Slack card → skills: [Slack Messenger]
    5. Builds Retriever card → capabilities: [docs_retrieval]
    6. Builds CustomAgent card with dependency_cards = {mcp, slack, retriever}
       → Composes: skills: [git_status, file_read, Slack Messenger]
                   capabilities: [docs_retrieval]
"""

from typing import Dict, List, Any
from collections import defaultdict
from core.enums import ResourceCategory
from core.element_meta import ElementConfigMeta
from elements.common.card.models import ElementCard, CardBuildInput, SpecMetadata
from elements.common.card.default import DefaultCardBuilder
from catalog.element_registry import ElementRegistry


class ElementCardService:
    """
    Builds ElementCards in dependency order.
    
    This service is the central orchestrator for card building.
    It ensures that when building a card for an element that references
    other elements, those dependency cards are already built and available.
    
    Accepts List[ElementConfigMeta] as input - callers are responsible for
    creating ElementConfigMeta from their own data structures (BlueprintSpec,
    ResourceDoc, SessionRegistry, etc.)
    """
    
    def __init__(self, element_registry: ElementRegistry):
        self._registry = element_registry
    
    def build_all_cards(
        self,
        configs: List[ElementConfigMeta]
    ) -> Dict[str, ElementCard]:
        """
        Build cards for all configs in dependency order.
        
        This is the main entry point for building cards from any source.
        
        Args:
            configs: List of ElementConfigMeta objects, each containing:
                     - rid: Resource ID
                     - category: ResourceCategory
                     - type_key: Element type
                     - name: User-defined name
                     - config: Pydantic config model
                     - dependency_rids: Pre-computed list of referenced rids
        
        Returns:
            Dictionary mapping resource ID to built ElementCard.
        """
        # Build lookup map for configs
        config_map = {meta.rid: meta for meta in configs}
        
        # Build dependency graph from pre-computed dependency_rids
        deps = self._build_dependency_graph(configs)
        
        # Topological sort
        order = self._topological_sort(list(config_map.keys()), deps)
        
        # Build cards in order
        cards: Dict[str, ElementCard] = {}
        
        for rid in order:
            meta = config_map[rid]
            
            # Get already-built dependency cards
            dep_cards = {
                dep_rid: cards[dep_rid]
                for dep_rid in deps.get(rid, [])
                if dep_rid in cards
            }
            
            card = self._build_single_card(meta, dep_cards)
            cards[rid] = card
        
        return cards
    
    def build_single_card(
        self,
        config: ElementConfigMeta,
        dependency_cards: Dict[str, ElementCard] = None
    ) -> ElementCard:
        """
        Build a single element card.
        
        Use this when:
        - Building a card for a leaf element (no dependencies)
        - Dependency cards are already available
        - Building a card for a single resource
        
        Args:
            config: ElementConfigMeta for the element
            dependency_cards: Optional dict of already-built dependency cards
            
        Returns:
            ElementCard for the element
        """
        return self._build_single_card(config, dependency_cards or {})
    
    def _build_single_card(
        self,
        meta: ElementConfigMeta,
        dependency_cards: Dict[str, ElementCard]
    ) -> ElementCard:
        """Internal: Build a single card with dependency cards."""
        spec = self._registry.get_spec(meta.category, meta.type_key)
        
        spec_metadata = SpecMetadata(
            category=spec.category,
            type_key=spec.type_key,
            name=spec.name,
            description=spec.description,
            capability_names=list(getattr(spec, 'capability_names', []))
        )
        
        build_input = CardBuildInput(
            rid=meta.rid,
            name=meta.name,
            config=meta.config,
            spec_metadata=spec_metadata,
            dependency_cards=dependency_cards
        )
        
        builder_cls = getattr(spec, 'card_builder_cls', DefaultCardBuilder)
        builder = builder_cls()
        
        return builder.build(build_input)
    
    def _build_dependency_graph(
        self,
        configs: List[ElementConfigMeta]
    ) -> Dict[str, List[str]]:
        """
        Build dependency graph from pre-computed dependency_rids.
        
        No need to walk configs - dependencies are already extracted by callers.
        """
        deps: Dict[str, List[str]] = defaultdict(list)
        config_rids = {meta.rid for meta in configs}
        
        for meta in configs:
            for dep_rid in meta.dependency_rids:
                # Only include deps that are in our config set
                if dep_rid in config_rids:
                    deps[meta.rid].append(dep_rid)
        
        return dict(deps)
    
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

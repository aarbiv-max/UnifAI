"""
Agent Inventory for Builder Tools.

Provides a unified interface for discovering reusable agents across
different inventory sources (custom agents, A2A agents, etc.).

Patterns:
- Protocol: Interface contracts for dependency injection
- BaseModel: Pydantic DTOs for agent data
- ABC: Abstract base for inventory implementations
- Strategy: Each inventory type has its own discovery logic
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging

from pydantic import BaseModel, Field

# Import the official protocol from builder protocols (avoid duplication)
from elements.nodes.builder.protocols import ResourcesServiceProtocol


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class InventoryType(str, Enum):
    """Available agent inventory types."""
    CUSTOM_AGENTS = "custom_agents"
    A2A_AGENTS = "a2a_agents"


# ---------------------------------------------------------------------------
# Text Matching Utility
# ---------------------------------------------------------------------------

class SkillMatcher:
    """
    Utility for matching required capabilities to agent skills.
    
    Uses flexible text matching that handles:
    - Substring matching (e.g., "chart" in "create_chart")
    - Compound words (e.g., "chart_generator" → check "chart" and "generator")
    - Common word forms (e.g., "charting" → "chart")
    
    This allows matching capabilities like "chart_generator" to skills like "create_chart"
    by extracting the meaningful parts of compound words.
    """
    
    # Common suffixes to strip for root matching
    SUFFIXES = ("ing", "tion", "ment", "ics", "er", "or", "s", "ed", "ly")
    
    # Separators for compound words
    SEPARATORS = ("_", "-", " ", ".")
    
    @classmethod
    def matches(cls, capability: str, searchable_text: str) -> bool:
        """
        Check if a capability matches within searchable text.
        
        Matching strategies (in order):
        1. Direct substring match
        2. Split compound words and check each part
        3. Root word match (remove suffixes from each part)
        
        Args:
            capability: The required capability (e.g., "chart_generator")
            searchable_text: Text to search in (lowercase)
            
        Returns:
            True if capability matches, False otherwise
        """
        cap_lower = capability.lower().strip()
        text_lower = searchable_text.lower()
        
        # Direct match
        if cap_lower in text_lower:
            return True
        
        # Split compound words and check each part
        parts = cls._split_compound(cap_lower)
        for part in parts:
            if len(part) < 3:  # Skip very short parts
                continue
            
            # Check part directly
            if part in text_lower:
                return True
            
            # Check roots of the part
            for root in cls._get_roots(part):
                if len(root) >= 3 and root in text_lower:
                    return True
        
        return False
    
    @classmethod
    def match_any(cls, capabilities: Set[str], searchable_text: str) -> List[str]:
        """
        Find all capabilities that match in searchable text.
        
        Args:
            capabilities: Set of required capabilities
            searchable_text: Text to search in
            
        Returns:
            List of matched capabilities
        """
        text_lower = searchable_text.lower()
        return [cap for cap in capabilities if cls.matches(cap, text_lower)]
    
    @classmethod
    def _split_compound(cls, word: str) -> List[str]:
        """
        Split compound words into parts.
        
        Examples:
            "chart_generator" → ["chart", "generator"]
            "data-analysis" → ["data", "analysis"]
            "jira" → ["jira"]
        """
        parts = []
        current = word
        
        for sep in cls.SEPARATORS:
            if sep in current:
                parts.extend(p.strip() for p in current.split(sep) if p.strip())
                return parts
        
        # No separator found, return the word itself
        return [word]
    
    @classmethod
    def _get_roots(cls, word: str) -> List[str]:
        """Extract word roots by removing common suffixes."""
        roots = []
        for suffix in cls.SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                roots.append(word[:-len(suffix)])
        return roots


# ---------------------------------------------------------------------------
# Agent Info DTO
# ---------------------------------------------------------------------------

class AgentInfo(BaseModel):
    """
    Unified agent information from any inventory.
    
    Pydantic model for clean serialization and validation.
    This is the common format returned by all inventory types.
    """
    rid: str = Field(..., description="Resource ID")
    name: str = Field(..., description="Agent name")
    source_type: InventoryType = Field(..., description="Inventory source")
    node_type: str = Field(..., description="Node type key")
    matched_capabilities: List[str] = Field(default_factory=list)
    description: str = Field(default="")
    
    # Custom agent fields
    system_message: Optional[str] = None
    llm: Optional[str] = None
    provider: Optional[str] = None
    retriever: Optional[str] = None
    
    # A2A agent fields
    base_url: Optional[str] = None
    bearer_token: Optional[str] = None
    agent_card_name: Optional[str] = None
    agent_card_description: Optional[str] = None
    agent_card_skills: List[str] = Field(default_factory=list)
    agent_card_skill_descriptions: List[str] = Field(default_factory=list)
    agent_card_tags: List[str] = Field(default_factory=list)
    
    def is_a2a(self) -> bool:
        """Check if this is an A2A agent."""
        return self.source_type == InventoryType.A2A_AGENTS
    
    def is_custom(self) -> bool:
        """Check if this is a custom agent."""
        return self.source_type == InventoryType.CUSTOM_AGENTS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for search results (backward compatible)."""
        return self.to_search_result()
    
    def to_search_result(self) -> Dict[str, Any]:
        """Convert to search result dictionary for builder tools."""
        result = {
            "rid": self.rid,
            "name": self.name,
            "type": self.node_type,
            "source": self.source_type.value,
            "matched_capabilities": self.matched_capabilities,
        }
        
        if self.is_custom():
            result.update({
                "system_message": self.system_message or "",
                "llm": self.llm,
                "provider": self.provider,
                "retriever": self.retriever,
            })
        elif self.is_a2a():
            result.update({
                "base_url": self.base_url,
                "bearer_token": self.bearer_token,
                "agent_card_name": self.agent_card_name,
                "agent_card_description": self.agent_card_description,
                "agent_card_skills": self.agent_card_skills,
                "agent_card_skill_descriptions": self.agent_card_skill_descriptions,
                "agent_card_tags": self.agent_card_tags,
            })
        
        return result
    
    def to_blueprint_node(self, index: int = 0) -> Dict[str, Any]:
        """Convert to blueprint node representation."""
        if self.is_a2a():
            return self._to_a2a_node(index)
        return self._to_custom_node(index)
    
    def _to_a2a_node(self, index: int) -> Dict[str, Any]:
        """Convert A2A agent to blueprint node."""
        config = {"type": "a2a_agent_node", "base_url": self.base_url}
        if self.bearer_token:
            config["bearer_token"] = self.bearer_token
        return {
            "rid": f"existing_a2a_{index}_rid",
            "name": self.name,
            "type": "a2a_agent_node",
            "config": config,
        }
    
    def _to_custom_node(self, index: int) -> Dict[str, Any]:
        """Convert custom agent to blueprint node."""
        config = {
            "type": "custom_agent_node",
            "system_message": self.system_message or "",
        }
        
        # Add refs for linked resources
        for field, value in [("llm", self.llm), ("provider", self.provider), ("retriever", self.retriever)]:
            if value:
                ref = value if str(value).startswith("$ref:") else f"$ref:{value}"
                config[field] = ref
        
        return {
            "rid": f"existing_agent_{index}_rid",
            "name": self.name,
            "type": "custom_agent_node",
            "config": config,
        }
    
    def get_searchable_text(self) -> str:
        """
        Build searchable text corpus from agent metadata.
        Used for capability matching.
        """
        texts = [self.name, self.description]
        
        if self.is_a2a():
            texts.extend([
                self.agent_card_name or "",
                self.agent_card_description or "",
            ])
            texts.extend(self.agent_card_skills)
            texts.extend(self.agent_card_skill_descriptions)
            texts.extend(self.agent_card_tags)
        elif self.is_custom():
            texts.append(self.system_message or "")
        
        return " ".join(t.lower() for t in texts if t)


# ---------------------------------------------------------------------------
# Abstract Inventory
# ---------------------------------------------------------------------------

class AgentInventory(ABC):
    """
    Abstract base for agent inventory implementations.
    
    Each subclass implements discovery logic for a specific agent type.
    """
    
    @property
    @abstractmethod
    def inventory_type(self) -> InventoryType:
        """Return the inventory type identifier."""
        ...
    
    @property
    @abstractmethod
    def node_type(self) -> str:
        """Return the node type key for this inventory."""
        ...
    
    @abstractmethod
    def search(
        self,
        resources_service: ResourcesServiceProtocol,
        user_id: str,
        capability_filter: Optional[List[str]] = None,
        provider_list: Optional[List[Dict[str, Any]]] = None,
        limit: int = 50,
    ) -> List[AgentInfo]:
        """
        Search for agents in this inventory.
        
        Args:
            resources_service: Service for accessing resources
            user_id: User ID for filtering
            capability_filter: Optional list of required capabilities
            provider_list: Optional list of provider configs (for matching)
            limit: Maximum results
            
        Returns:
            List of matching AgentInfo objects
        """
        ...


# ---------------------------------------------------------------------------
# Custom Agent Inventory
# ---------------------------------------------------------------------------

class CustomAgentInventory(AgentInventory):
    """
    Inventory for custom_agent_node resources.
    
    Custom agents are user-defined agents with LLM, provider, and retriever.
    Matching is based on provider capabilities.
    """
    
    @property
    def inventory_type(self) -> InventoryType:
        return InventoryType.CUSTOM_AGENTS
    
    @property
    def node_type(self) -> str:
        return "custom_agent_node"
    
    def search(
        self,
        resources_service: ResourcesServiceProtocol,
        user_id: str,
        capability_filter: Optional[List[str]] = None,
        provider_list: Optional[List[Dict[str, Any]]] = None,
        limit: int = 50,
    ) -> List[AgentInfo]:
        """Search for custom agents."""
        try:
            nodes, _ = resources_service.find_resources(
                user_id=user_id,
                category="nodes",
                type=self.node_type,
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"Custom agent search failed: {e}")
            return []
        
        agents = []
        # Build mapping: provider_rid -> capabilities that provider matches
        provider_caps_map = self._build_provider_caps_map(provider_list) if provider_list else {}
        
        for node in nodes:
            try:
                cfg = node.cfg_dict or {}
                agent_info = self._build_agent_info(node, cfg, capability_filter, provider_caps_map)
                if agent_info:
                    agents.append(agent_info)
            except Exception as e:
                logger.warning(f"Error processing custom agent {getattr(node, 'rid', '?')}: {e}")
                continue
        
        # Sort by match relevance
        agents.sort(key=lambda a: (len(a.matched_capabilities) == 0, a.name))
        return agents
    
    def _build_provider_caps_map(
        self, 
        provider_list: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Build mapping of provider RID to its matched capabilities.
        
        This ensures custom agents only get capabilities that their
        specific provider actually matches, not all requested capabilities.
        """
        caps_map: Dict[str, List[str]] = {}
        for provider in provider_list:
            rid = str(provider.get("rid", ""))
            if rid:
                # Get the capabilities this specific provider matched
                matched_caps = provider.get("matched_capabilities", [])
                caps_map[rid] = matched_caps
        return caps_map
    
    def _build_agent_info(
        self,
        node: Any,
        cfg: Dict[str, Any],
        capability_filter: Optional[List[str]],
        provider_caps_map: Dict[str, List[str]],
    ) -> Optional[AgentInfo]:
        """Build AgentInfo from node data."""
        # Extract provider reference
        provider_ref = cfg.get("provider")
        provider_rid = None
        if provider_ref:
            provider_rid = str(provider_ref).replace("$ref:", "").strip()
        
        # Match by provider - only get capabilities the provider actually matches
        matched = []
        if provider_rid and provider_rid in provider_caps_map:
            # Get only the capabilities this specific provider handles
            matched = provider_caps_map[provider_rid]
        
        # Only include if matched or no filter
        if not capability_filter or matched:
            return AgentInfo(
                rid=node.rid,
                name=node.name or "Custom Agent",
                source_type=self.inventory_type,
                node_type=self.node_type,
                matched_capabilities=matched,
                description="",
                system_message=cfg.get("system_message", ""),
                llm=self._extract_ref(cfg.get("llm")),
                provider=provider_rid,
                retriever=self._extract_ref(cfg.get("retriever")),
            )
        return None
    
    @staticmethod
    def _extract_ref(value: Any) -> Optional[str]:
        """Extract RID from a $ref: value."""
        if not value:
            return None
        return str(value).replace("$ref:", "").strip()


# ---------------------------------------------------------------------------
# A2A Agent Inventory
# ---------------------------------------------------------------------------

class A2AAgentInventory(AgentInventory):
    """
    Inventory for a2a_agent_node resources.
    
    A2A agents are remote agents with agent_card metadata.
    Matching is based on skills, description, and tags.
    """
    
    @property
    def inventory_type(self) -> InventoryType:
        return InventoryType.A2A_AGENTS
    
    @property
    def node_type(self) -> str:
        return "a2a_agent_node"
    
    def search(
        self,
        resources_service: ResourcesServiceProtocol,
        user_id: str,
        capability_filter: Optional[List[str]] = None,
        provider_list: Optional[List[Dict[str, Any]]] = None,
        limit: int = 50,
    ) -> List[AgentInfo]:
        """
        Search for A2A agents.
        
        Returns all A2A agents, with matched_capabilities populated
        for those matching the filter.
        """
        try:
            nodes, _ = resources_service.find_resources(
                user_id=user_id,
                category="nodes",
                type=self.node_type,
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"A2A agent search failed: {e}")
            return []
        
        agents = []
        for node in nodes:
            try:
                agent_info = self._build_agent_info(node, capability_filter)
                agents.append(agent_info)
            except Exception as e:
                logger.warning(f"Error processing A2A agent {getattr(node, 'rid', '?')}: {e}")
                continue
        
        # Sort: matched first, then by name
        agents.sort(key=lambda a: (len(a.matched_capabilities) == 0, a.name))
        return agents
    
    def _build_agent_info(
        self,
        node: Any,
        capability_filter: Optional[List[str]],
    ) -> AgentInfo:
        """Build AgentInfo from A2A node data."""
        cfg = node.cfg_dict or {}
        agent_card = cfg.get("agent_card", {}) or {}
        
        # Extract skills
        skills = agent_card.get("skills", []) or []
        skill_names = [s.get("name", "") for s in skills if isinstance(s, dict)]
        skill_descs = [s.get("description", "") for s in skills if isinstance(s, dict)]
        tags = agent_card.get("tags", []) or []
        
        agent_info = AgentInfo(
            rid=node.rid,
            name=node.name or agent_card.get("name", "A2A Agent"),
            source_type=self.inventory_type,
            node_type=self.node_type,
            matched_capabilities=[],
            description=agent_card.get("description", ""),
            base_url=str(cfg.get("base_url", "")),
            bearer_token=cfg.get("bearer_token"),
            agent_card_name=agent_card.get("name", ""),
            agent_card_description=agent_card.get("description", ""),
            agent_card_skills=skill_names,
            agent_card_skill_descriptions=skill_descs,
            agent_card_tags=tags,
        )
        
        # Match capabilities using searchable text
        if capability_filter:
            searchable = agent_info.get_searchable_text()
            agent_info.matched_capabilities = SkillMatcher.match_any(
                set(capability_filter), searchable
            )
        
        return agent_info

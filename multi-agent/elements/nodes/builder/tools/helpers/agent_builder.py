"""
AgentBuilder helper for creating agent nodes in blueprints.

Handles:
- Reusing existing agents from search results (custom agents and A2A agents)
- Creating new agents from providers
- Creating LLM-only agents for capabilities without providers

Note: A2A agents are only REUSED, never created by the builder.
Creating A2A agents requires external configuration (endpoint URL, etc.).
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from .agent_inventory import SkillMatcher


@dataclass
class AgentBuildResult:
    """Result from agent building process."""
    agent_nodes: List[Dict[str, Any]] = field(default_factory=list)
    created_agent_rids: List[str] = field(default_factory=list)
    used_capabilities: Set[str] = field(default_factory=set)
    agents_created: int = 0
    agents_reused: int = 0
    custom_agents_reused: int = 0
    a2a_agents_reused: int = 0


class AgentBuilder:
    """
    Builds agent nodes for workflow blueprints.
    
    Follows a priority order:
    1. Reuse existing A2A agents that match required capabilities (remote, no LLM needed)
    2. Reuse existing custom agents that match required capabilities
    3. Create new agents for providers matching required capabilities
    4. Create LLM-only agents for remaining capabilities
    
    A2A agents are prioritized when they have explicit skill matches,
    as they represent specialized remote agents.
    """
    
    def __init__(
        self,
        llm_rid: str,
        resources_service: Any = None,
        user_id: str = ""
    ):
        """
        Initialize the agent builder.
        
        Args:
            llm_rid: RID of the LLM to use for new agents
            resources_service: Optional service for creating agent resources
            user_id: User ID for resource creation
        """
        self.llm_rid = llm_rid
        self.resources_service = resources_service
        self.user_id = user_id
    
    def build_agents(
        self,
        existing_agents: List[Dict[str, Any]],
        matched_providers: List[Dict[str, Any]],
        required_capabilities: Set[str],
        existing_a2a_agents: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentBuildResult:
        """
        Build agent nodes based on available resources and requirements.
        
        Args:
            existing_agents: Custom agents from search results to potentially reuse
            matched_providers: Providers that match required capabilities
            required_capabilities: Set of required capability strings
            existing_a2a_agents: A2A agents from search results to potentially reuse
            
        Returns:
            AgentBuildResult with created agent nodes and metadata
        """
        result = AgentBuildResult()
        a2a_agents = existing_a2a_agents or []
        
        # Step 1: Select A2A agents whose skills match required capabilities
        # Each A2A agent has agent_card.skills - match these to requirements
        matching_a2a = self._match_a2a_by_skills(a2a_agents, required_capabilities)
        self._add_a2a_agents(matching_a2a, result)
        
        # Step 2: Add existing custom agents
        self._add_existing_agents(existing_agents, result)
        
        # Step 3: Create agents for providers (only for capabilities not yet covered)
        self._create_provider_agents(
            matched_providers, 
            required_capabilities, 
            result
        )
        
        # Step 4: Create LLM-only agents for missing capabilities
        self._create_llm_only_agents(required_capabilities, result)
        
        # Calculate counts
        result.agents_reused = result.custom_agents_reused + result.a2a_agents_reused
        result.agents_created = len(result.created_agent_rids)
        
        return result
    
    def _match_a2a_by_skills(
        self,
        a2a_agents: List[Dict[str, Any]],
        required_capabilities: Set[str]
    ) -> List[Dict[str, Any]]:
        """
        Match A2A agents by their skills to required capabilities.
        
        Uses SkillMatcher for flexible text matching across agent metadata:
        - skill names and descriptions
        - agent description
        - tags
        
        Example:
            Required: ["charting"]
            Agent skills: ["create_chart"]
            Match: "chart" root found in "create_chart" → Agent selected
        """
        if not required_capabilities:
            return a2a_agents
        
        matched = []
        for agent in a2a_agents:
            corpus = self._build_agent_corpus(agent)
            if SkillMatcher.match_any(required_capabilities, corpus):
                matched.append(agent)
        
        return matched
    
    def _build_agent_corpus(self, agent: Dict[str, Any]) -> str:
        """Build searchable text from A2A agent metadata."""
        texts = [
            agent.get("name", ""),
            agent.get("agent_card_name", ""),
            agent.get("agent_card_description", ""),
        ]
        texts.extend(agent.get("agent_card_skills", []) or [])
        texts.extend(agent.get("agent_card_skill_descriptions", []) or [])
        texts.extend(agent.get("agent_card_tags", []) or [])
        
        return " ".join(str(t).lower() for t in texts if t)
    
    def _add_a2a_agents(
        self,
        a2a_agents: List[Dict[str, Any]],
        result: AgentBuildResult
    ) -> None:
        """
        Add A2A agents to the blueprint.
        
        A2A agents are self-contained remote agents. They don't need
        local LLM or provider configuration.
        
        We inline the full config from the existing resource. The base_url
        must be a valid URL that was validated when the resource was created.
        """
        for i, agent in enumerate(a2a_agents):
            agent_caps = agent.get("matched_capabilities", [])
            for cap in agent_caps:
                result.used_capabilities.add(cap.lower())
            
            # Get the base_url - must be a valid URL
            base_url = agent.get("base_url", "")
            if not base_url:
                # Skip if no base_url available - A2A agents require it
                continue
            
            agent_rid = f"existing_a2a_{i}_rid"
            
            # A2A agent config with full inline configuration
            agent_node_config = {
                "type": "a2a_agent_node",
                "base_url": base_url,
            }
            
            # Include bearer_token if present (for authentication)
            bearer_token = agent.get("bearer_token")
            if bearer_token:
                agent_node_config["bearer_token"] = bearer_token
            
            # Blueprint node structure (no extra fields - forbid mode!)
            agent_config = {
                "rid": agent_rid,
                "name": agent.get("name", f"A2A Agent {i+1}"),
                "type": "a2a_agent_node",
                "config": agent_node_config,
            }
            result.agent_nodes.append(agent_config)
            result.a2a_agents_reused += 1
    
    def _add_existing_agents(
        self,
        existing_agents: List[Dict[str, Any]],
        result: AgentBuildResult
    ) -> None:
        """Add existing custom agents with full inline configuration."""
        for i, agent in enumerate(existing_agents):
            agent_caps = agent.get("matched_capabilities", [])
            for cap in agent_caps:
                result.used_capabilities.add(cap.lower())
            
            agent_rid = f"existing_agent_{i}_rid"
            agent_llm = self._normalize_ref(agent.get("llm"), self.llm_rid)
            agent_provider = self._normalize_ref(agent.get("provider"))
            
            agent_node_config = {
                "type": "custom_agent_node",
                "llm": agent_llm,
                "system_message": agent.get("system_message", ""),
            }
            
            if agent_provider:
                agent_node_config["provider"] = agent_provider
            if agent.get("retriever"):
                agent_node_config["retriever"] = self._normalize_ref(
                    agent.get("retriever")
                )
            
            # Blueprint node structure (no extra fields - forbid mode!)
            agent_config = {
                "rid": agent_rid,
                "name": agent.get("name", f"Agent {i+1}"),
                "type": "custom_agent_node",
                "config": agent_node_config,
            }
            result.agent_nodes.append(agent_config)
            result.custom_agents_reused += 1
    
    def _create_provider_agents(
        self,
        matched_providers: List[Dict[str, Any]],
        required_capabilities: Set[str],
        result: AgentBuildResult
    ) -> None:
        """Create agents for providers that match required capabilities."""
        new_agent_count = 0
        
        for provider in matched_providers:
            provider_caps = provider.get("matched_capabilities", [])
            provider_name = provider.get("name", "Unknown")
            
            # Filter to only required capabilities
            if required_capabilities:
                matching_required = [
                    cap for cap in provider_caps 
                    if cap.lower() in required_capabilities
                ]
                if not matching_required:
                    continue
                provider_caps = matching_required
            
            # Skip if already handled by existing agents (custom or A2A)
            if all(cap.lower() in result.used_capabilities for cap in provider_caps):
                continue
            
            provider_rid = provider.get("rid")
            provider_tools = provider.get("tools", [])
            agent_name = f"{provider_name} Agent"
            
            tools_desc = ", ".join(provider_tools[:3]) if provider_tools else "available tools"
            system_message = (
                f"You are an agent that uses {provider_name} to help with tasks. "
                f"Available tools: {tools_desc}."
            )
            
            agent_config = self._create_or_get_agent(
                agent_name=agent_name,
                system_message=system_message,
                provider_rid=provider_rid,
                fallback_rid=f"new_agent_{new_agent_count}_rid"
            )
            
            if agent_config:
                if agent_config.get("_created"):
                    result.created_agent_rids.append(agent_config["rid"])
                    del agent_config["_created"]
                result.agent_nodes.append(agent_config)
            
            for cap in provider_caps:
                result.used_capabilities.add(cap.lower())
            new_agent_count += 1
    
    def _create_llm_only_agents(
        self,
        required_capabilities: Set[str],
        result: AgentBuildResult
    ) -> None:
        """Create LLM-only agents for capabilities without providers."""
        missing_caps = required_capabilities - result.used_capabilities
        
        for cap in missing_caps:
            agent_name = f"{cap.title()} Agent"
            system_message = (
                f"You are a specialized {cap} agent. "
                f"Help users with {cap}-related tasks using your knowledge "
                "and reasoning abilities."
            )
            
            agent_config = self._create_or_get_agent(
                agent_name=agent_name,
                system_message=system_message,
                provider_rid=None,
                fallback_rid=f"llm_agent_{cap}_rid"
            )
            
            if agent_config:
                if agent_config.get("_created"):
                    result.created_agent_rids.append(agent_config["rid"])
                    del agent_config["_created"]
                result.agent_nodes.append(agent_config)
            
            result.used_capabilities.add(cap.lower())
    
    def _create_or_get_agent(
        self,
        agent_name: str,
        system_message: str,
        provider_rid: Optional[str],
        fallback_rid: str
    ) -> Optional[Dict[str, Any]]:
        """Create a new agent resource or return inline config."""
        agent_config_dict = {
            "type": "custom_agent_node",
            "llm": f"$ref:{self.llm_rid}",
            "system_message": system_message,
        }
        if provider_rid:
            agent_config_dict["provider"] = f"$ref:{provider_rid}"
        
        saved_agent_rid = None
        created = False
        
        if self.resources_service:
            try:
                existing_docs, _ = self.resources_service.find_resources(
                    user_id=self.user_id,
                    category="nodes",
                    type="custom_agent_node",
                )
                
                matching_agent = None
                for doc in existing_docs:
                    if doc.name and doc.name.lower() == agent_name.lower():
                        matching_agent = doc
                        break
                
                if matching_agent:
                    saved_agent_rid = matching_agent.rid
                else:
                    doc = self.resources_service.create(
                        user_id=self.user_id,
                        category="nodes",
                        type="custom_agent_node",
                        name=agent_name,
                        config=agent_config_dict,
                    )
                    saved_agent_rid = doc.rid
                    created = True
            except Exception:
                pass
        
        rid = saved_agent_rid or fallback_rid
        
        config = {
            "rid": rid,
            "name": agent_name,
            "type": "custom_agent_node",
            "config": agent_config_dict,
        }
        
        if created:
            config["_created"] = True
        
        return config
    
    def _normalize_ref(
        self, 
        value: Optional[str], 
        default: Optional[str] = None
    ) -> Optional[str]:
        """Normalize a reference to $ref: format."""
        if not value:
            if default:
                return f"$ref:{default}"
            return None
        
        if isinstance(value, str) and value.startswith("$ref:"):
            return value
        
        return f"$ref:{value}"

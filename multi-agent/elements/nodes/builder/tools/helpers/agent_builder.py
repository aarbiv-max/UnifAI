"""
AgentBuilder helper for creating agent nodes in blueprints.

Handles:
- Reusing existing agents from search results
- Creating new agents from providers
- Creating LLM-only agents for capabilities without providers
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class AgentBuildResult:
    """Result from agent building process."""
    agent_nodes: List[Dict[str, Any]] = field(default_factory=list)
    created_agent_rids: List[str] = field(default_factory=list)
    used_capabilities: Set[str] = field(default_factory=set)
    agents_created: int = 0
    agents_reused: int = 0


class AgentBuilder:
    """
    Builds agent nodes for workflow blueprints.
    
    Follows a priority order:
    1. Reuse existing agents that match required capabilities
    2. Create new agents for providers matching required capabilities
    3. Create LLM-only agents for remaining capabilities
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
        required_capabilities: Set[str]
    ) -> AgentBuildResult:
        """
        Build agent nodes based on available resources and requirements.
        
        Args:
            existing_agents: Agents from search results to potentially reuse
            matched_providers: Providers that match required capabilities
            required_capabilities: Set of required capability strings
            
        Returns:
            AgentBuildResult with created agent nodes and metadata
        """
        result = AgentBuildResult()
        
        # Step 1: Add existing agents
        self._add_existing_agents(existing_agents, result)
        
        # Step 2: Create agents for providers
        self._create_provider_agents(
            matched_providers, 
            required_capabilities, 
            result
        )
        
        # Step 3: Create LLM-only agents for missing capabilities
        self._create_llm_only_agents(required_capabilities, result)
        
        # Calculate counts
        result.agents_reused = len([
            a for a in result.agent_nodes 
            if a.get("rid", "").startswith("existing_agent_")
        ])
        result.agents_created = len(result.created_agent_rids)
        
        return result
    
    def _add_existing_agents(
        self,
        existing_agents: List[Dict[str, Any]],
        result: AgentBuildResult
    ) -> None:
        """Add existing agents with full inline configuration."""
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
            
            agent_config = {
                "rid": agent_rid,
                "name": agent.get("name", f"Agent {i+1}"),
                "type": "custom_agent_node",
                "config": agent_node_config,
            }
            result.agent_nodes.append(agent_config)
    
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
            
            # Skip if already handled
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


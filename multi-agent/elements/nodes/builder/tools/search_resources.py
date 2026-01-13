"""
Search Resources Tool for the Builder Agent.

Searches for available LLMs, providers, and existing agents in the user's account.
Supports searching across multiple agent inventories (custom agents, A2A agents, etc.).
"""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from elements.tools.common.base_tool import BaseTool
from ..context import BuilderContext, ResourceSearchResult
from .helpers import inventory_registry, InventoryType


class SearchResourcesArgs(BaseModel):
    """Arguments for searching resources."""
    capability_filter: Optional[List[str]] = Field(
        default=None,
        description="Optional list of capabilities to filter providers (e.g., ['jira', 'confluence', 'slack'])"
    )
    include_existing_agents: bool = Field(
        default=True,
        description="Whether to include existing agent nodes in the search"
    )
    agent_inventories: Optional[List[str]] = Field(
        default=None,
        description=(
            "Which agent inventories to search. Options: 'custom_agents', 'a2a_agents'. "
            "Default: all inventories. Use this to limit search to specific agent types."
        )
    )


class SearchResourcesTool(BaseTool):
    """
    Search for available resources in the user's account.
    
    Searches for:
    - LLMs (mandatory for any workflow)
    - Providers/MCPs (for external tool access)
    - Existing agent nodes (custom agents, A2A agents) for potential reuse
    """
    
    name = "search_resources"
    description = """Search for available resources in the user's account.

Returns:
- LLMs: Available language models (at least one is required for any workflow)
- Providers: Available MCP providers (e.g., Jira, Confluence, Slack)
- Existing Agents: Agent nodes that could be reused (custom agents and A2A agents)

Use this to understand what resources are available before designing the workflow.
You can optionally filter by capability (e.g., 'jira' to find Jira-related providers).
You can also specify which agent inventories to search (custom_agents, a2a_agents)."""
    
    args_schema = SearchResourcesArgs
    
    def __init__(self, get_context: Callable[[], BuilderContext]):
        """
        Initialize the tool.
        
        Args:
            get_context: Callable to get the builder context
        """
        self._get_context = get_context
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Search for available resources."""
        args = SearchResourcesArgs(**kwargs)
        context = self._get_context()
        
        if not context or not context.resources_service:
            return {
                "success": False,
                "error": "Resources service not available",
            }
        
        resources_service = context.resources_service
        user_id = context.user_id
        
        try:
            # Search for LLMs
            llms, _ = resources_service.find_resources(
                user_id=user_id,
                category="llms",
                limit=50
            )
            
            # Search for providers
            providers, _ = resources_service.find_resources(
                user_id=user_id,
                category="providers",
                limit=50
            )
            
            # Format LLM results
            llm_list = [
                {
                    "rid": llm.rid,
                    "name": llm.name,
                    "type": llm.type,
                }
                for llm in llms
            ]
            
            # Format provider results with capability matching
            provider_list = self._process_providers(providers, args.capability_filter)
            
            # Search for orchestrators (always search, separate from agent inventories)
            orchestrator_list = self._search_orchestrators(resources_service, user_id)
            
            # Search agents using inventory registry
            custom_agent_list = []
            a2a_agent_list = []
            
            if args.include_existing_agents:
                # Parse inventory types from args
                inv_types = inventory_registry.parse_inventory_types(args.agent_inventories)
                
                # Search agents using registry
                agent_results = inventory_registry.search(
                    resources_service=resources_service,
                    user_id=user_id,
                    inventories=inv_types,
                    capability_filter=args.capability_filter,
                    provider_list=provider_list,
                    limit=50,
                )
                
                # Separate results by type
                if InventoryType.CUSTOM_AGENTS in agent_results:
                    custom_agent_list = [
                        agent.to_dict() 
                        for agent in agent_results[InventoryType.CUSTOM_AGENTS]
                    ]
                
                if InventoryType.A2A_AGENTS in agent_results:
                    a2a_agent_list = [
                        agent.to_dict() 
                        for agent in agent_results[InventoryType.A2A_AGENTS]
                    ]
            
            # Check for missing capabilities
            missing = self._find_missing_capabilities(
                args.capability_filter, 
                provider_list,
                custom_agent_list,
                a2a_agent_list,
            )
            
            # Create result
            result = ResourceSearchResult(
                llms=llm_list,
                providers=provider_list,
                existing_nodes=custom_agent_list,
                existing_a2a_agents=a2a_agent_list,
                existing_orchestrators=orchestrator_list,
                missing_capabilities=missing,
                has_required_llm=len(llm_list) > 0,
            )
            
            # Update context state (don't advance phase - node manages that)
            context.state.search_result = result
            
            # Build summary
            total_agents = len(custom_agent_list) + len(a2a_agent_list)
            summary_parts = [
                f"{len(llm_list)} LLMs",
                f"{len(provider_list)} providers",
            ]
            if custom_agent_list:
                summary_parts.append(f"{len(custom_agent_list)} custom agents")
            if a2a_agent_list:
                summary_parts.append(f"{len(a2a_agent_list)} A2A agents")
            if orchestrator_list:
                summary_parts.append(f"{len(orchestrator_list)} orchestrators")
            
            summary = f"Found {', '.join(summary_parts)}"

            return {
                "success": True,
                "phase_complete": True,  # Signal that search is done
                "llms": llm_list,
                "providers": provider_list,
                "existing_agents": custom_agent_list,  # Backward compatible
                "existing_a2a_agents": a2a_agent_list,
                "existing_orchestrators": orchestrator_list,
                "has_required_llm": len(llm_list) > 0,
                "missing_capabilities": missing,
                "summary": summary,
                "agent_inventory_stats": {
                    "custom_agents": len(custom_agent_list),
                    "a2a_agents": len(a2a_agent_list),
                    "total": total_agents,
                },
                "next_action": "PHASE COMPLETE - Resources found. Do NOT call this tool again. Summarize findings and complete this phase.",
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error searching resources: {str(e)}",
            }
    
    def _process_providers(
        self, 
        providers: List[Any], 
        capability_filter: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Process and filter providers by capability."""
        provider_list = []
        
        for provider in providers:
            provider_info = {
                "rid": provider.rid,
                "name": provider.name,
                "type": provider.type,
            }
            
            # Extract capability hints from config
            cfg = provider.cfg_dict or {}
            if "tool_names" in cfg:
                provider_info["tools"] = cfg["tool_names"][:5]
            
            # Apply capability filter if provided
            if capability_filter:
                provider_name_lower = provider.name.lower()
                
                matched_caps = []
                for cap in capability_filter:
                    cap_lower = cap.lower()
                    if cap_lower in provider_name_lower:
                        matched_caps.append(cap_lower)
                
                if matched_caps:
                    provider_info["matched_capabilities"] = matched_caps
                    provider_list.append(provider_info)
            else:
                provider_list.append(provider_info)
        
        return provider_list
    
    def _search_orchestrators(
        self, 
        resources_service: Any, 
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Search for existing orchestrator nodes."""
        orchestrator_list = []
        
        try:
            nodes, _ = resources_service.find_resources(
                user_id=user_id,
                category="nodes",
                type="orchestrator_node",
                limit=50
            )
            
            for node in nodes:
                cfg = node.cfg_dict or {}
                orchestrator_list.append({
                    "rid": node.rid,
                    "name": node.name,
                    "type": node.type,
                    "system_message": cfg.get("system_message", ""),
                    "llm": cfg.get("llm"),
                })
        except Exception:
            pass
        
        return orchestrator_list
    
    def _find_missing_capabilities(
        self,
        capability_filter: Optional[List[str]],
        provider_list: List[Dict[str, Any]],
        custom_agent_list: List[Dict[str, Any]],
        a2a_agent_list: List[Dict[str, Any]],
    ) -> List[str]:
        """Find capabilities that weren't matched by any resource."""
        if not capability_filter:
            return []
        
        found_caps = set()
        
        # Check providers
        for provider in provider_list:
            for tool in provider.get("tools", []):
                for cap in capability_filter:
                    if cap.lower() in tool.lower():
                        found_caps.add(cap.lower())
            # Also check matched_capabilities
            for cap in provider.get("matched_capabilities", []):
                found_caps.add(cap.lower())
        
        # Check custom agents
        for agent in custom_agent_list:
            for cap in agent.get("matched_capabilities", []):
                found_caps.add(cap.lower())
        
        # Check A2A agents
        for agent in a2a_agent_list:
            for cap in agent.get("matched_capabilities", []):
                found_caps.add(cap.lower())
        
        # Find missing
        missing = [
            cap for cap in capability_filter 
            if cap.lower() not in found_caps
        ]
        
        return missing

"""
Search Resources Tool for the Builder Agent.

Searches for available LLMs, providers, and existing agents in the user's account.
"""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from elements.tools.common.base_tool import BaseTool
from ..context import BuilderContext, ResourceSearchResult


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


class SearchResourcesTool(BaseTool):
    """
    Search for available resources in the user's account.
    
    Searches for:
    - LLMs (mandatory for any workflow)
    - Providers/MCPs (for external tool access)
    - Existing agent nodes (for potential reuse)
    """
    
    name = "search_resources"
    description = """Search for available resources in the user's account.

Returns:
- LLMs: Available language models (at least one is required for any workflow)
- Providers: Available MCP providers (e.g., Jira, Confluence, Slack)
- Existing Agents: Agent nodes that could be reused

Use this to understand what resources are available before designing the workflow.
You can optionally filter by capability (e.g., 'jira' to find Jira-related providers)."""
    
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
            
            # Search for existing nodes (agents)
            nodes = []
            if args.include_existing_agents:
                nodes, _ = resources_service.find_resources(
                    user_id=user_id,
                    category="nodes",
                    limit=50
                )
            
            # Format results
            llm_list = [
                {
                    "rid": llm.rid,
                    "name": llm.name,
                    "type": llm.type,
                }
                for llm in llms
            ]
            
            provider_list = []
            provider_cap_map = {}  # Track which capability matched which provider
            
            for provider in providers:
                provider_info = {
                    "rid": provider.rid,
                    "name": provider.name,
                    "type": provider.type,
                }
                
                # Try to extract capability hints from config
                cfg = provider.cfg_dict or {}
                if "tool_names" in cfg:
                    provider_info["tools"] = cfg["tool_names"][:5]  # First 5 tools
                
                # Apply capability filter if provided
                if args.capability_filter:
                    # Check which specific capabilities match this provider
                    # STRICT matching: only match on provider NAME (not tool names)
                    # This prevents Confluence matching "jira" because of shared Atlassian tools
                    provider_name_lower = provider.name.lower()
                    
                    matched_caps = []
                    for cap in args.capability_filter:
                        cap_lower = cap.lower()
                        # Only match if capability is directly in the provider name
                        if cap_lower in provider_name_lower:
                            matched_caps.append(cap_lower)
                    
                    if matched_caps:
                        provider_info["matched_capabilities"] = matched_caps
                        provider_list.append(provider_info)
                        for cap in matched_caps:
                            if cap not in provider_cap_map:
                                provider_cap_map[cap] = provider_info
                else:
                    provider_list.append(provider_info)
            
            # Filter agents by capability if specified
            node_list = []
            orchestrator_list = []  # Track existing orchestrators separately
            agent_cap_map = {}  # Track which capability matched which existing agent
            
            for node in nodes:
                # Track orchestrator nodes separately
                if node.type == "orchestrator_node":
                    cfg = node.cfg_dict or {}
                    orchestrator_list.append({
                        "rid": node.rid,
                        "name": node.name,
                        "type": node.type,
                        "system_message": cfg.get("system_message", ""),
                        "llm": cfg.get("llm"),
                    })
                    continue
                
                if node.type not in ["custom_agent_node"]:
                    continue  # Only custom agents can be reused
                
                cfg = node.cfg_dict or {}
                node_info = {
                    "rid": node.rid,
                    "name": node.name,
                    "type": node.type,
                    "system_message": cfg.get("system_message", ""),  # Full system message
                    "llm": cfg.get("llm"),
                    "provider": cfg.get("provider"),
                    "retriever": cfg.get("retriever"),  # Include retriever if any
                }
                
                if args.capability_filter:
                    # Check multiple sources for capability matching:
                    # 1. Agent name (STRICT: capability must be in name)
                    # 2. Agent's attached provider (STRICT: provider must match this capability)
                    # NOTE: We do NOT match on system_message as it's too loose
                    agent_name_lower = node.name.lower() if node.name else ""
                    
                    matched_caps = []
                    for cap in args.capability_filter:
                        cap_lower = cap.lower()
                        
                        # Check if capability matches agent name DIRECTLY
                        if cap_lower in agent_name_lower:
                            matched_caps.append(cap_lower)
                            continue
                        
                        # Check if capability matches agent's provider
                        # ONLY if the PROVIDER itself matched this capability
                        provider_ref = cfg.get("provider")
                        if provider_ref:
                            provider_rid = provider_ref.replace("$ref:", "") if isinstance(provider_ref, str) and provider_ref.startswith("$ref:") else provider_ref
                            matching_provider = next(
                                (p for p in provider_list if p["rid"] == provider_rid),
                                None
                            )
                            if matching_provider:
                                # STRICT: Only match if the provider also matched this capability
                                provider_matched_caps = matching_provider.get("matched_capabilities", [])
                                if cap_lower in provider_matched_caps:
                                    matched_caps.append(cap_lower)
                                    continue
                    
                    if matched_caps:
                        node_info["matched_capabilities"] = matched_caps
                        node_list.append(node_info)
                        # Track which capability this agent can handle
                        for cap in matched_caps:
                            if cap not in agent_cap_map:
                                agent_cap_map[cap] = node_info
                else:
                    node_list.append(node_info)
            
            # Check for missing capabilities
            missing = []
            if args.capability_filter:
                found_caps = set()
                for provider in provider_list:
                    for tool in provider.get("tools", []):
                        for cap in args.capability_filter:
                            if cap.lower() in tool.lower():
                                found_caps.add(cap.lower())
                
                missing = [
                    cap for cap in args.capability_filter 
                    if cap.lower() not in found_caps
                ]
            
            # Create result
            result = ResourceSearchResult(
                llms=llm_list,
                providers=provider_list,
                existing_nodes=node_list,
                existing_orchestrators=orchestrator_list,
                missing_capabilities=missing,
                has_required_llm=len(llm_list) > 0,
            )
            
            # Update context state (don't advance phase - node manages that)
            context.state.search_result = result

            return {
                "success": True,
                "phase_complete": True,  # Signal that search is done
                "llms": llm_list,
                "providers": provider_list,
                "existing_agents": node_list,
                "existing_orchestrators": orchestrator_list,
                "has_required_llm": len(llm_list) > 0,
                "missing_capabilities": missing,
                "summary": f"Found {len(llm_list)} LLMs, {len(provider_list)} providers, {len(node_list)} existing agents, {len(orchestrator_list)} orchestrators",
                "next_action": "PHASE COMPLETE - Resources found. Do NOT call this tool again. Summarize findings and complete this phase.",
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error searching resources: {str(e)}",
            }


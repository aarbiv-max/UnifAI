"""
Create Agent Tool for the Builder Agent.

Creates new agent resources in the user's library.
"""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from elements.tools.common.base_tool import BaseTool
from ..context import BuilderContext


class CreateAgentArgs(BaseModel):
    """Arguments for creating a new agent."""
    name: str = Field(
        description="Display name for the agent (e.g., 'Jira Search Agent')"
    )
    system_message: str = Field(
        description="System prompt describing the agent's role and behavior"
    )
    llm_rid: str = Field(
        description="Resource ID of the LLM to use for this agent"
    )
    provider_rid: Optional[str] = Field(
        default=None,
        description="Optional resource ID of an MCP provider for tool access"
    )
    strategy_type: str = Field(
        default="react",
        description="Agent strategy type ('react' for tool-using, 'plan_and_execute' for complex tasks)"
    )


class CreateAgentTool(BaseTool):
    """
    Create a new agent resource in the user's library.
    
    The agent will be saved as a resource that can be referenced
    in the workflow blueprint.
    """
    
    name = "create_agent"
    description = """Create a new agent resource in the user's library.

Args:
    name: Display name for the agent
    system_message: System prompt describing the agent's role
    llm_rid: Resource ID of the LLM to use (from search_resources results)
    provider_rid: Optional MCP provider resource ID for tool access
    strategy_type: Agent strategy ('react' or 'plan_and_execute')

Returns the resource ID of the created agent which can be used in the workflow blueprint.

Example:
    create_agent(
        name="Jira Search Agent",
        system_message="You are a Jira search specialist. Help users find and analyze Jira issues.",
        llm_rid="abc123",
        provider_rid="mcp_jira_456"
    )"""
    
    args_schema = CreateAgentArgs
    
    def __init__(self, get_context: Callable[[], BuilderContext]):
        """
        Initialize the tool.
        
        Args:
            get_context: Callable to get the builder context
        """
        self._get_context = get_context
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Create a new agent resource."""
        args = CreateAgentArgs(**kwargs)
        context = self._get_context()
        
        if not context or not context.resources_service:
            return {
                "success": False,
                "error": "Resources service not available",
            }
        
        resources_service = context.resources_service
        user_id = context.user_id
        
        try:
            # Format LLM reference - ensure $ref: prefix
            llm_ref = args.llm_rid
            if not llm_ref.startswith("$ref:"):
                llm_ref = f"$ref:{llm_ref}"
            
            # Build agent config
            agent_config = {
                "type": "custom_agent_node",
                "llm": llm_ref,
                "system_message": args.system_message,
                "strategy_type": args.strategy_type,
            }
            
            # Add provider if specified - ensure $ref: prefix
            if args.provider_rid:
                provider_ref = args.provider_rid
                if not provider_ref.startswith("$ref:"):
                    provider_ref = f"$ref:{provider_ref}"
                agent_config["provider"] = provider_ref
            
            # Create the resource
            doc = resources_service.create(
                user_id=user_id,
                category="nodes",
                type="custom_agent_node",
                name=args.name,
                config=agent_config,
            )
            
            # Track created agent in context
            if context.state.design_result:
                context.state.design_result.created_agent_rids.append(doc.rid)
            
            # IMPORTANT: Add the new agent to search results so generate_blueprint will use it
            new_agent_info = {
                "rid": doc.rid,
                "name": doc.name,
                "type": doc.type,
                "system_message": args.system_message,
                "llm": llm_ref,  # Use the properly formatted $ref:
                "provider": agent_config.get("provider"),  # Use the properly formatted $ref:
                "matched_capabilities": [],  # New agent matches user's intended capabilities
            }
            
            if context.state.search_result:
                if context.state.search_result.existing_nodes is None:
                    context.state.search_result.existing_nodes = []
                context.state.search_result.existing_nodes.append(new_agent_info)
            
            return {
                "success": True,
                "rid": doc.rid,
                "name": doc.name,
                "type": doc.type,
                "message": f"Created agent '{args.name}' with ID: {doc.rid}. Agent added to workflow resources.",
                "agent_added_to_workflow": True,
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if agent already exists - try to find and use it
            if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                try:
                    # Search for existing agent with same name
                    existing_nodes, _ = resources_service.find_resources(
                        user_id=user_id,
                        category="nodes",
                        limit=100
                    )
                    
                    for node in existing_nodes:
                        if node.name and node.name.lower() == args.name.lower():
                            cfg = node.cfg_dict or {}
                            # Found existing agent - add to search results
                            existing_agent_info = {
                                "rid": node.rid,
                                "name": node.name,
                                "type": node.type,
                                "system_message": cfg.get("system_message", ""),
                                "llm": cfg.get("llm"),
                                "provider": cfg.get("provider"),
                                "matched_capabilities": [],
                            }
                            
                            if context.state.search_result:
                                if context.state.search_result.existing_nodes is None:
                                    context.state.search_result.existing_nodes = []
                                # Check if not already in list
                                existing_rids = [n.get("rid") for n in context.state.search_result.existing_nodes]
                                if node.rid not in existing_rids:
                                    context.state.search_result.existing_nodes.append(existing_agent_info)
                            
                            return {
                                "success": True,
                                "rid": node.rid,
                                "name": node.name,
                                "type": node.type,
                                "message": f"Agent '{args.name}' already exists (ID: {node.rid}). Using existing agent.",
                                "agent_added_to_workflow": True,
                                "existing_agent_used": True,
                            }
                except Exception:
                    pass  # If search fails, fall through to error
            
            return {
                "success": False,
                "error": f"Error creating agent: {error_msg}",
            }


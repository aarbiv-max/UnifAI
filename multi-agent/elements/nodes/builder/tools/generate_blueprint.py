"""
Generate Blueprint Tool for the Builder Agent.

Generates a workflow blueprint structure based on agents and requirements.
Uses actual resources found in the search phase.
"""

from typing import Any, Callable, Dict, List
from pydantic import BaseModel, Field

from elements.tools.common.base_tool import BaseTool
from ..context import BuilderContext, DesignResult
from ..exceptions import BuilderError, BuilderContextError, BuilderResourceError
from .helpers import AgentBuilder, PlanBuilder


class GenerateBlueprintArgs(BaseModel):
    """Arguments for generating a blueprint."""
    workflow_name: str = Field(
        description="Name of the workflow (e.g., 'Jira & Confluence Knowledge Assistant')"
    )
    workflow_description: str = Field(
        default="",
        description="Description of what the workflow does"
    )


class GenerateBlueprintTool(BaseTool):
    """
    Generate a workflow blueprint using resources from the search phase.
    
    Automatically uses the LLMs and agents found in the previous search.
    """
    
    name = "generate_blueprint"
    description = """Generate a workflow blueprint using the resources found in the search phase.

This tool automatically uses:
- The first available LLM from the search results
- Any existing agents that match the required capabilities
- Standard nodes (user_question, orchestrator, final_answer)

Just provide a name and optional description. The tool handles the rest based on search results.

Args:
    workflow_name: Name of the workflow
    workflow_description: Optional description of the workflow"""
    
    args_schema = GenerateBlueprintArgs
    
    def __init__(self, get_context: Callable[[], BuilderContext]):
        """
        Initialize the tool.
        
        Args:
            get_context: Callable to get the builder context
        """
        self._get_context = get_context
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Generate the workflow blueprint using search results."""
        args = GenerateBlueprintArgs(**kwargs)
        context = self._get_context()
        
        if not context:
            raise BuilderContextError()
        
        # Get resources from search phase
        search_result = context.state.search_result
        if not search_result:
            raise BuilderResourceError(
                resource_type="search_result",
                message="No search results. Run search_resources first."
            )
        
        analysis = context.state.analysis
        
        try:
            # Get the first available LLM (required)
            if not search_result.llms:
                raise BuilderResourceError(
                    resource_type="llm",
                    message="No LLM found. Cannot create workflow without an LLM."
                )
            
            llm_rid = search_result.llms[0]["rid"]
            llm_name = search_result.llms[0].get("name", "LLM")
            
            # Get required capabilities from analysis
            required_caps = set()
            if analysis and analysis.required_capabilities:
                required_caps = {cap.lower() for cap in analysis.required_capabilities}
            
            # Determine if orchestrator is needed
            existing_agents = search_result.existing_nodes or []
            needs_orchestrator = (
                (analysis and analysis.needs_orchestrator) or 
                len(existing_agents) > 1
            )
            
            # Build agents using helper
            agent_builder = AgentBuilder(
                llm_rid=llm_rid,
                resources_service=context.resources_service,
                user_id=context.user_id
            )
            
            agent_result = agent_builder.build_agents(
                existing_agents=existing_agents,
                matched_providers=search_result.providers or [],
                required_capabilities=required_caps
            )
            
            # Initialize blueprint structure
            blueprint = self._init_blueprint(args.workflow_name, args.workflow_description)
            
            # Add router condition if using orchestrator
            if needs_orchestrator:
                blueprint["conditions"].append({
                    "rid": "router_direct_rid",
                    "name": "Router",
                    "type": "router_direct",
                    "config": {"type": "router_direct"},
                })
            
            # Add required nodes
            self._add_required_nodes(blueprint)
            
            # Add orchestrator if needed
            orchestrator_rid = None
            if needs_orchestrator:
                orchestrator_rid = self._add_orchestrator_node(
                    blueprint=blueprint,
                    llm_rid=llm_rid,
                    existing_orchestrators=search_result.existing_orchestrators or [],
                    workflow_description=args.workflow_description
                )
            
            # Add agent nodes to blueprint
            for agent_node in agent_result.agent_nodes:
                blueprint["nodes"].append(agent_node)
            
            # Build the execution plan
            plan_builder = PlanBuilder()
            plan = plan_builder.build_plan(
                agent_nodes=agent_result.agent_nodes,
                needs_orchestrator=needs_orchestrator,
                orchestrator_rid=orchestrator_rid
            )
            blueprint["plan"] = plan
            
            # Build workflow summary
            summary = plan_builder.build_workflow_summary(
                agent_nodes=agent_result.agent_nodes,
                needs_orchestrator=needs_orchestrator
            )
            
            # Build agent details for response
            agent_details = self._build_agent_details(agent_result.agent_nodes)
            
            # Update context state
            design_result = DesignResult(
                blueprint_draft=blueprint,
                workflow_summary=summary,
                plan_description=f"Workflow with {len(agent_result.agent_nodes)} agent(s), LLM: {llm_name}",
                agents_created=agent_result.agents_created,
                agents_reused=agent_result.agents_reused,
                uses_orchestrator=needs_orchestrator,
                created_agent_rids=agent_result.created_agent_rids,
            )
            context.state.design_result = design_result
            
            return {
                "success": True,
                "phase_complete": True,
                "blueprint": blueprint,
                "summary": summary,
                "llm_used": {"rid": llm_rid, "name": llm_name},
                "agents": agent_details,
                "agents_created": agent_result.agents_created,
                "agents_reused": agent_result.agents_reused,
                "created_agent_rids": agent_result.created_agent_rids,
                "uses_orchestrator": needs_orchestrator,
                "message": f"Generated workflow: {summary}. Created {agent_result.agents_created} new agent(s) in inventory.",
                "next_action": "PHASE COMPLETE - Blueprint generated. Do NOT call this tool again. Summarize the workflow and complete this phase.",
            }
            
        except BuilderError as e:
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error generating blueprint: {str(e)}",
            }
    
    def _init_blueprint(self, name: str, description: str) -> Dict[str, Any]:
        """Initialize empty blueprint structure."""
        return {
            "name": name,
            "description": description,
            "providers": [],
            "llms": [],
            "retrievers": [],
            "tools": [],
            "conditions": [],
            "nodes": [],
            "plan": [],
        }
    
    def _add_required_nodes(self, blueprint: Dict[str, Any]) -> None:
        """Add user_question and final_answer nodes to blueprint."""
        blueprint["nodes"].append({
            "rid": "user_question_node_rid",
            "name": "User Question Node",
            "type": "user_question_node",
            "config": {"type": "user_question_node"},
        })
        
        blueprint["nodes"].append({
            "rid": "final_answer_node_rid",
            "name": "Final Answer Node",
            "type": "final_answer_node",
            "config": {"type": "final_answer_node"},
        })
    
    def _add_orchestrator_node(
        self,
        blueprint: Dict[str, Any],
        llm_rid: str,
        existing_orchestrators: List[Dict[str, Any]],
        workflow_description: str
    ) -> str:
        """Add orchestrator node to blueprint and return its RID."""
        if existing_orchestrators:
            # Use first existing orchestrator
            orch = existing_orchestrators[0]
            orchestrator_rid = "existing_orchestrator_rid"
            
            orch_llm = orch.get("llm")
            if not orch_llm:
                orch_llm = f"$ref:{llm_rid}"
            elif not str(orch_llm).startswith("$ref:"):
                orch_llm = f"$ref:{orch_llm}"
            
            blueprint["nodes"].append({
                "rid": orchestrator_rid,
                "name": orch.get("name", "Orchestrator"),
                "type": "orchestrator_node",
                "config": {
                    "type": "orchestrator_node",
                    "llm": orch_llm,
                    "system_message": orch.get(
                        "system_message", 
                        f"Orchestrate the workflow: {workflow_description}"
                    ),
                },
            })
        else:
            # Create new orchestrator
            orchestrator_rid = "orchestrator_node_rid"
            blueprint["nodes"].append({
                "rid": orchestrator_rid,
                "name": "Orchestrator",
                "type": "orchestrator_node",
                "config": {
                    "type": "orchestrator_node",
                    "llm": f"$ref:{llm_rid}",
                    "system_message": f"Orchestrate the workflow: {workflow_description}",
                },
            })
        
        return orchestrator_rid
    
    def _build_agent_details(
        self, 
        agent_nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Build agent details list for response."""
        agent_details = []
        for agent in agent_nodes:
            cfg = agent.get("config", {})
            llm_ref = cfg.get("llm", "").replace("$ref:", "") if cfg else ""
            provider_ref = cfg.get("provider", "").replace("$ref:", "") if cfg else ""
            agent_details.append({
                "name": agent.get("name", "Agent"),
                "llm": llm_ref,
                "provider": provider_ref,
            })
        return agent_details

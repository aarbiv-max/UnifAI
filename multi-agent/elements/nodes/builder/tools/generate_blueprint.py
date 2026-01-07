"""
Generate Blueprint Tool for the Builder Agent.

Generates a workflow blueprint structure based on agents and requirements.
Uses actual resources found in the search phase.
"""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from elements.tools.common.base_tool import BaseTool
from ..context import BuilderContext, DesignResult


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
            return {"success": False, "error": "Builder context not available"}
        
        # Get resources from search phase
        search_result = context.state.search_result
        if not search_result:
            return {"success": False, "error": "No search results. Run search_resources first."}
        
        analysis = context.state.analysis
        
        try:
            # Get the first available LLM (required)
            if not search_result.llms:
                return {"success": False, "error": "No LLM found. Cannot create workflow without an LLM."}
            
            llm_rid = search_result.llms[0]["rid"]
            llm_name = search_result.llms[0].get("name", "LLM")
            
            # Get existing agents to reuse
            existing_agents = search_result.existing_nodes or []
            
            # Determine if orchestrator is needed
            needs_orchestrator = (analysis and analysis.needs_orchestrator) or len(existing_agents) > 1
            
            # Build the blueprint structure
            blueprint = {
                "name": args.workflow_name,
                "description": args.workflow_description,
                "providers": [],
                "llms": [],
                "retrievers": [],
                "tools": [],
                "conditions": [],
                "nodes": [],
                "plan": [],
            }
            
            # Add router condition if using orchestrator
            if needs_orchestrator:
                blueprint["conditions"].append({
                    "rid": "router_direct_rid",
                    "name": "Router",
                    "type": "router_direct",
                    "config": {"type": "router_direct"},
                })
            
            # Add required nodes
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
            
            # Add orchestrator if needed - prefer existing one
            orchestrator_node_rid = None
            if needs_orchestrator:
                existing_orchestrators = search_result.existing_orchestrators or []
                
                if existing_orchestrators:
                    # Use first existing orchestrator with full inline config
                    orch = existing_orchestrators[0]
                    orchestrator_node_rid = "existing_orchestrator_rid"
                    
                    # Get LLM ref - ensure proper format
                    orch_llm = orch.get("llm")
                    if not orch_llm:
                        orch_llm = f"$ref:{llm_rid}"
                    elif not str(orch_llm).startswith("$ref:"):
                        orch_llm = f"$ref:{orch_llm}"
                    
                    blueprint["nodes"].append({
                        "rid": orchestrator_node_rid,
                        "name": orch.get("name", "Orchestrator"),
                        "type": "orchestrator_node",
                        "config": {
                            "type": "orchestrator_node",
                            "llm": orch_llm,
                            "system_message": orch.get("system_message", f"Orchestrate the workflow: {args.workflow_description}"),
                        },
                    })
                else:
                    # Create new inline orchestrator
                    orchestrator_node_rid = "orchestrator_node_rid"
                    blueprint["nodes"].append({
                        "rid": orchestrator_node_rid,
                        "name": "Orchestrator",
                        "type": "orchestrator_node",
                        "config": {
                            "type": "orchestrator_node",
                            "llm": f"$ref:{llm_rid}",
                            "system_message": f"Orchestrate the workflow: {args.workflow_description}",
                        },
                    })
            
            # Strategy: Prefer existing agents, only create new ones if needed
            # 1. First, use existing agents that match the required capabilities
            # 2. For capabilities without existing agents, create new inline agents
            
            existing_agents_to_use = search_result.existing_nodes or []
            matched_providers = search_result.providers or []
            
            print(f"[generate_blueprint] Existing agents from search: {[(a.get('name'), a.get('matched_capabilities', [])) for a in existing_agents_to_use]}")
            print(f"[generate_blueprint] Matched providers from search: {[(p.get('name'), p.get('matched_capabilities', [])) for p in matched_providers]}")
            
            agent_nodes = []
            used_capabilities = set()
            
            # Step 1: Add existing agents with their FULL configuration (inline copy)
            for i, agent in enumerate(existing_agents_to_use):
                agent_caps = agent.get("matched_capabilities", [])
                print(f"[generate_blueprint] REUSE existing agent '{agent.get('name')}' with caps: {agent_caps}")
                for cap in agent_caps:
                    used_capabilities.add(cap.lower())
                
                # Create inline copy with full agent details
                agent_rid = f"existing_agent_{i}_rid"
                
                # Get LLM ref - ensure proper format
                agent_llm = agent.get("llm")
                if not agent_llm:
                    agent_llm = f"$ref:{llm_rid}"
                elif not str(agent_llm).startswith("$ref:"):
                    agent_llm = f"$ref:{agent_llm}"
                
                # Get provider ref - ensure proper format (if exists)
                agent_provider = agent.get("provider")
                if agent_provider and not str(agent_provider).startswith("$ref:"):
                    agent_provider = f"$ref:{agent_provider}"
                
                # Build config - only include fields that exist
                agent_node_config = {
                    "type": "custom_agent_node",
                    "llm": agent_llm,
                    "system_message": agent.get("system_message", ""),
                }
                if agent_provider:
                    agent_node_config["provider"] = agent_provider
                if agent.get("retriever"):
                    retriever_ref = agent.get("retriever")
                    if not str(retriever_ref).startswith("$ref:"):
                        retriever_ref = f"$ref:{retriever_ref}"
                    agent_node_config["retriever"] = retriever_ref
                
                agent_config = {
                    "rid": agent_rid,
                    "name": agent.get("name", f"Agent {i+1}"),
                    "type": "custom_agent_node",
                    "config": agent_node_config,
                }
                agent_nodes.append(agent_config)
                blueprint["nodes"].append(agent_config)
            
            # Step 2: For providers without existing agents, CREATE NEW AGENTS AS RESOURCES
            # These agents will be saved to the inventory and referenced via $ref
            new_agent_count = 0
            created_agent_rids = []
            
            resources_service = context.resources_service
            user_id = context.user_id
            
            # Get REQUIRED capabilities from analysis
            required_caps = set()
            if analysis and analysis.required_capabilities:
                required_caps = {cap.lower() for cap in analysis.required_capabilities}
            
            print(f"[generate_blueprint] Required capabilities: {required_caps}")
            print(f"[generate_blueprint] Matched providers: {[(p.get('name'), p.get('matched_capabilities', [])) for p in matched_providers]}")
            
            for provider in matched_providers:
                provider_caps = provider.get("matched_capabilities", [])
                provider_name = provider.get("name", "Unknown")
                
                print(f"[generate_blueprint] Checking provider '{provider_name}' with caps: {provider_caps}")
                
                # Skip if provider doesn't match any REQUIRED capability
                if required_caps:
                    matching_required = [cap for cap in provider_caps if cap.lower() in required_caps]
                    if not matching_required:
                        print(f"[generate_blueprint] SKIP '{provider_name}' - caps {provider_caps} don't match required: {required_caps}")
                        continue
                    provider_caps = matching_required  # Only use the matching required capabilities
                    print(f"[generate_blueprint] USE '{provider_name}' - matched required caps: {provider_caps}")
                
                # Skip if all capabilities are already handled by existing agents
                if all(cap.lower() in used_capabilities for cap in provider_caps):
                    print(f"[generate_blueprint] SKIP '{provider_name}' - caps {provider_caps} already in used_capabilities: {used_capabilities}")
                    continue
                
                provider_rid = provider.get("rid")
                provider_name = provider.get("name", f"Provider {new_agent_count+1}")
                provider_tools = provider.get("tools", [])
                
                agent_name = f"{provider_name} Agent"
                
                # Build system message based on provider capabilities
                tools_desc = ", ".join(provider_tools[:3]) if provider_tools else "available tools"
                system_message = f"You are an agent that uses {provider_name} to help with tasks. Available tools: {tools_desc}."
                
                # Create the agent as a RESOURCE in the inventory
                print(f"[generate_blueprint] Creating agent for provider '{provider_name}', resources_service={resources_service is not None}")
                if resources_service:
                    try:
                        print(f"[generate_blueprint] Building agent config for '{agent_name}'")
                        agent_config_dict = {
                            "type": "custom_agent_node",
                            "llm": f"$ref:{llm_rid}",
                            "provider": f"$ref:{provider_rid}",
                            "system_message": system_message,
                        }
                        
                        # Check if agent with this name already exists
                        # find_resources doesn't support name filter, so we get all and filter
                        existing_docs, _ = resources_service.find_resources(
                            user_id=user_id,
                            category="nodes",
                            type="custom_agent_node",
                        )
                        
                        # Filter by name manually
                        matching_agent = None
                        for doc in existing_docs:
                            if doc.name and doc.name.lower() == agent_name.lower():
                                matching_agent = doc
                                break
                        
                        if matching_agent:
                            # Use existing agent
                            saved_agent_rid = matching_agent.rid
                            print(f"Found existing agent '{agent_name}' with RID: {saved_agent_rid}")
                        else:
                            # Create new agent resource
                            doc = resources_service.create(
                                user_id=user_id,
                                category="nodes",
                                type="custom_agent_node",
                                name=agent_name,
                                config=agent_config_dict,
                            )
                            saved_agent_rid = doc.rid
                            print(f"Created new agent '{agent_name}' with RID: {saved_agent_rid}")
                        
                        created_agent_rids.append(saved_agent_rid)
                        
                        # Add FULL inline node definition so the workflow displays correctly
                        # Even though the agent is saved to inventory, the blueprint needs the full config
                        agent_config = {
                            "rid": saved_agent_rid,  # Use the inventory RID
                            "name": agent_name,
                            "type": "custom_agent_node",
                            "config": {
                                "type": "custom_agent_node",
                                "llm": f"$ref:{llm_rid}",
                                "provider": f"$ref:{provider_rid}",
                                "system_message": system_message,
                            },
                        }
                        agent_nodes.append(agent_config)
                        blueprint["nodes"].append(agent_config)
                        
                    except Exception as e:
                        print(f"Warning: Failed to create agent resource: {e}")
                        # Fallback to inline agent if resource creation fails
                        agent_rid = f"new_agent_{new_agent_count}_rid"
                        agent_config = {
                            "rid": agent_rid,
                            "name": agent_name,
                            "type": "custom_agent_node",
                            "config": {
                                "type": "custom_agent_node",
                                "llm": f"$ref:{llm_rid}",
                                "provider": f"$ref:{provider_rid}",
                                "system_message": system_message,
                            },
                        }
                        agent_nodes.append(agent_config)
                        blueprint["nodes"].append(agent_config)
                else:
                    # No resources service - create inline agent (fallback)
                    agent_rid = f"new_agent_{new_agent_count}_rid"
                    agent_config = {
                        "rid": agent_rid,
                        "name": agent_name,
                        "type": "custom_agent_node",
                        "config": {
                            "type": "custom_agent_node",
                            "llm": f"$ref:{llm_rid}",
                            "provider": f"$ref:{provider_rid}",
                            "system_message": system_message,
                        },
                    }
                    agent_nodes.append(agent_config)
                    blueprint["nodes"].append(agent_config)
                
                for cap in provider_caps:
                    used_capabilities.add(cap.lower())
                new_agent_count += 1
            
            # Step 3: Create LLM-only agents for capabilities that don't have matching providers
            # This handles cases like "sales agent" when there's no "sales" provider
            missing_caps = required_caps - used_capabilities
            if missing_caps:
                print(f"[generate_blueprint] Creating LLM-only agents for missing capabilities: {missing_caps}")
                
                for cap in missing_caps:
                    # Create an agent for this capability using just an LLM (no provider)
                    agent_name = f"{cap.title()} Agent"
                    system_message = f"You are a specialized {cap} agent. Help users with {cap}-related tasks using your knowledge and reasoning abilities."
                    
                    if resources_service:
                        try:
                            agent_config_dict = {
                                "type": "custom_agent_node",
                                "llm": f"$ref:{llm_rid}",
                                "system_message": system_message,
                                # No provider - this is an LLM-only agent
                            }
                            
                            # Check if agent with this name already exists
                            existing_docs, _ = resources_service.find_resources(
                                user_id=user_id,
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
                                print(f"[generate_blueprint] Found existing LLM-only agent '{agent_name}' with RID: {saved_agent_rid}")
                            else:
                                doc = resources_service.create(
                                    user_id=user_id,
                                    category="nodes",
                                    type="custom_agent_node",
                                    name=agent_name,
                                    config=agent_config_dict,
                                )
                                saved_agent_rid = doc.rid
                                print(f"[generate_blueprint] Created new LLM-only agent '{agent_name}' with RID: {saved_agent_rid}")
                            
                            created_agent_rids.append(saved_agent_rid)
                            
                            # Add inline node definition
                            agent_config = {
                                "rid": saved_agent_rid,
                                "name": agent_name,
                                "type": "custom_agent_node",
                                "config": {
                                    "type": "custom_agent_node",
                                    "llm": f"$ref:{llm_rid}",
                                    "system_message": system_message,
                                },
                            }
                            agent_nodes.append(agent_config)
                            blueprint["nodes"].append(agent_config)
                            
                        except Exception as e:
                            print(f"Warning: Failed to create LLM-only agent for '{cap}': {e}")
                            # Fallback to inline agent
                            agent_rid = f"llm_agent_{cap}_rid"
                            agent_config = {
                                "rid": agent_rid,
                                "name": agent_name,
                                "type": "custom_agent_node",
                                "config": {
                                    "type": "custom_agent_node",
                                    "llm": f"$ref:{llm_rid}",
                                    "system_message": system_message,
                                },
                            }
                            agent_nodes.append(agent_config)
                            blueprint["nodes"].append(agent_config)
                    else:
                        # No resources service - create inline agent
                        agent_rid = f"llm_agent_{cap}_rid"
                        agent_config = {
                            "rid": agent_rid,
                            "name": agent_name,
                            "type": "custom_agent_node",
                            "config": {
                                "type": "custom_agent_node",
                                "llm": f"$ref:{llm_rid}",
                                "system_message": system_message,
                            },
                        }
                        agent_nodes.append(agent_config)
                        blueprint["nodes"].append(agent_config)
                    
                    used_capabilities.add(cap.lower())
                    new_agent_count += 1
            
            # Track created agents in design result
            if context.state.design_result is None:
                context.state.design_result = DesignResult()
            context.state.design_result.created_agent_rids = created_agent_rids
            
            # Use agent_nodes for the plan - all nodes are defined inline
            all_agents = agent_nodes
            
            # Build the plan
            plan = []
            
            # User input step
            plan.append({
                "uid": "user_input",
                "node": "user_question_node_rid",
            })
            
            if needs_orchestrator and all_agents:
                # Orchestrator pattern with multiple agents
                agent_uids = [f"agent_{i}" for i in range(len(all_agents))]
                after_list = ["user_input"] + agent_uids
                
                branches = {uid: uid for uid in agent_uids}
                branches["finalize"] = "finalize"
                
                plan.append({
                    "uid": "orchestrator",
                    "after": after_list,
                    "node": orchestrator_node_rid,
                    "exit_condition": "router_direct_rid",
                    "branches": branches,
                })
                
                # Add agent steps - all nodes are now defined inline in the blueprint
                for i, agent in enumerate(all_agents):
                    agent_rid = agent.get("rid", f"agent_{i}_rid")
                    
                    # Use the RID directly (node is defined inline in blueprint["nodes"])
                    plan.append({
                        "uid": f"agent_{i}",
                        "node": agent_rid,
                    })
                
                # Finalize
                plan.append({
                    "uid": "finalize",
                    "node": "final_answer_node_rid",
                })
            elif all_agents:
                # Single agent, no orchestrator
                agent = all_agents[0]
                agent_rid = agent.get("rid", "agent_0_rid")
                
                # Use the RID directly (node is defined inline in blueprint["nodes"])
                plan.append({
                    "uid": "agent_0",
                    "after": "user_input",
                    "node": agent_rid,
                })
                plan.append({
                    "uid": "finalize",
                    "after": "agent_0",
                    "node": "final_answer_node_rid",
                })
            else:
                # No agents, direct flow
                plan.append({
                    "uid": "finalize",
                    "after": "user_input",
                    "node": "final_answer_node_rid",
                })
            
            # Replace agent_nodes reference for summary building
            existing_agents = all_agents
            
            blueprint["plan"] = plan
            
            # Build summary with detailed agent info
            agent_details = []
            for agent in existing_agents:
                agent_name = agent.get("name", "Agent")
                cfg = agent.get("config", {})
                llm_ref = cfg.get("llm", "").replace("$ref:", "") if cfg else ""
                provider_ref = cfg.get("provider", "").replace("$ref:", "") if cfg else ""
                agent_details.append({
                    "name": agent_name,
                    "llm": llm_ref,
                    "provider": provider_ref,
                })
            
            agent_names = [a["name"] for a in agent_details]
            if needs_orchestrator:
                summary = f"user_question -> orchestrator -> [{', '.join(agent_names)}] -> final_answer"
            elif agent_names:
                summary = f"user_question -> {agent_names[0]} -> final_answer"
            else:
                summary = "user_question -> final_answer"
            
            # Update context state
            # Count created vs reused agents
            created_count = len(created_agent_rids)
            reused_count = len(all_agents) - created_count
            
            design_result = DesignResult(
                blueprint_draft=blueprint,
                workflow_summary=summary,
                plan_description=f"Workflow with {len(existing_agents)} agent(s), LLM: {llm_name}",
                agents_created=created_count,
                agents_reused=reused_count,
                uses_orchestrator=needs_orchestrator,
            )
            context.state.design_result = design_result
            
            return {
                "success": True,
                "phase_complete": True,  # Signal that design is done
                "blueprint": blueprint,
                "summary": summary,
                "llm_used": {"rid": llm_rid, "name": llm_name},
                "agents": agent_details,  # Include full agent details
                "agents_created": created_count,  # Number of new agents saved to inventory
                "agents_reused": reused_count,    # Number of existing agents reused
                "created_agent_rids": created_agent_rids,
                "uses_orchestrator": needs_orchestrator,
                "message": f"Generated workflow: {summary}. Created {created_count} new agent(s) in inventory.",
                "next_action": "PHASE COMPLETE - Blueprint generated. Do NOT call this tool again. Summarize the workflow and complete this phase.",
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error generating blueprint: {str(e)}",
            }


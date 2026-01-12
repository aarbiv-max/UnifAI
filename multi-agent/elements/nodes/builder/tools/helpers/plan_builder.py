"""
PlanBuilder helper for creating workflow execution plans.

Handles:
- Building plan steps with proper ordering
- Adding orchestrator patterns for multi-agent workflows
- Creating direct flows for single-agent workflows
"""

from typing import Any, Dict, List, Optional


class PlanBuilder:
    """
    Builds execution plans for workflow blueprints.
    
    Supports:
    - Single agent flows: user_question -> agent -> final_answer
    - Orchestrated flows: user_question -> orchestrator -> [agents] -> final_answer
    """
    
    def __init__(
        self,
        user_question_rid: str = "user_question_node_rid",
        final_answer_rid: str = "final_answer_node_rid"
    ):
        """
        Initialize the plan builder.
        
        Args:
            user_question_rid: RID of the user question node
            final_answer_rid: RID of the final answer node
        """
        self.user_question_rid = user_question_rid
        self.final_answer_rid = final_answer_rid
    
    def build_plan(
        self,
        agent_nodes: List[Dict[str, Any]],
        needs_orchestrator: bool,
        orchestrator_rid: Optional[str] = None,
        condition_rid: str = "router_direct_rid"
    ) -> List[Dict[str, Any]]:
        """
        Build the execution plan for a workflow.
        
        Args:
            agent_nodes: List of agent node configurations
            needs_orchestrator: Whether to use orchestrator pattern
            orchestrator_rid: RID of the orchestrator node (if using orchestrator)
            condition_rid: RID of the routing condition
            
        Returns:
            List of plan steps
        """
        plan = []
        
        # Always start with user input
        plan.append({
            "uid": "user_input",
            "node": self.user_question_rid,
        })
        
        if needs_orchestrator and agent_nodes and orchestrator_rid:
            # Orchestrator pattern
            plan.extend(
                self._build_orchestrator_plan(
                    agent_nodes, 
                    orchestrator_rid, 
                    condition_rid
                )
            )
        elif agent_nodes:
            # Single agent pattern
            plan.extend(self._build_single_agent_plan(agent_nodes[0]))
        else:
            # No agents - direct flow
            plan.extend(self._build_direct_flow())
        
        return plan
    
    def _build_orchestrator_plan(
        self,
        agent_nodes: List[Dict[str, Any]],
        orchestrator_rid: str,
        condition_rid: str
    ) -> List[Dict[str, Any]]:
        """Build plan steps for orchestrator pattern."""
        steps = []
        
        agent_uids = [f"agent_{i}" for i in range(len(agent_nodes))]
        after_list = ["user_input"] + agent_uids
        
        # Build branches mapping
        branches = {uid: uid for uid in agent_uids}
        branches["finalize"] = "finalize"
        
        # Orchestrator step
        steps.append({
            "uid": "orchestrator",
            "after": after_list,
            "node": orchestrator_rid,
            "exit_condition": condition_rid,
            "branches": branches,
        })
        
        # Agent steps
        for i, agent in enumerate(agent_nodes):
            agent_rid = agent.get("rid", f"agent_{i}_rid")
            steps.append({
                "uid": f"agent_{i}",
                "node": agent_rid,
            })
        
        # Finalize step
        steps.append({
            "uid": "finalize",
            "node": self.final_answer_rid,
        })
        
        return steps
    
    def _build_single_agent_plan(
        self,
        agent: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build plan steps for single agent pattern."""
        agent_rid = agent.get("rid", "agent_0_rid")
        
        return [
            {
                "uid": "agent_0",
                "after": "user_input",
                "node": agent_rid,
            },
            {
                "uid": "finalize",
                "after": "agent_0",
                "node": self.final_answer_rid,
            }
        ]
    
    def _build_direct_flow(self) -> List[Dict[str, Any]]:
        """Build plan steps for direct flow (no agents)."""
        return [
            {
                "uid": "finalize",
                "after": "user_input",
                "node": self.final_answer_rid,
            }
        ]
    
    def build_workflow_summary(
        self,
        agent_nodes: List[Dict[str, Any]],
        needs_orchestrator: bool
    ) -> str:
        """
        Build a human-readable workflow summary.
        
        Args:
            agent_nodes: List of agent node configurations
            needs_orchestrator: Whether orchestrator is used
            
        Returns:
            Summary string describing the workflow flow
        """
        agent_names = [a.get("name", "Agent") for a in agent_nodes]
        
        if needs_orchestrator and agent_names:
            return (
                f"user_question -> orchestrator -> "
                f"[{', '.join(agent_names)}] -> final_answer"
            )
        elif agent_names:
            return f"user_question -> {agent_names[0]} -> final_answer"
        else:
            return "user_question -> final_answer"


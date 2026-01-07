"""
Preview Workflow Tool for the Builder Agent.

Formats the workflow for user approval before saving.
"""

from typing import Any, Callable, Dict, List
from pydantic import BaseModel, Field

from elements.tools.common.base_tool import BaseTool
from ..context import BuilderContext


class PreviewWorkflowArgs(BaseModel):
    """Arguments for previewing a workflow."""
    include_full_blueprint: bool = Field(
        default=False,
        description="Whether to include the full blueprint JSON in the preview"
    )


class PreviewWorkflowTool(BaseTool):
    """
    Format the workflow for user approval.
    
    Creates a human-readable preview of the workflow including:
    - Workflow name and description
    - List of agents and their roles
    - Flow summary
    - Resources used
    - Any validation warnings
    """
    
    name = "preview_workflow"
    description = """Format the workflow for user approval.

Creates a summary of the workflow that the user can review before approving.
Shows:
- Workflow name and description
- Agents included and their purposes
- Workflow flow (how data moves between nodes)
- Resources being used (LLMs, providers)
- Any warnings from validation

Call this after validation passes to present the workflow for approval."""
    
    args_schema = PreviewWorkflowArgs
    
    def __init__(self, get_context: Callable[[], BuilderContext]):
        """
        Initialize the tool.
        
        Args:
            get_context: Callable to get the builder context
        """
        self._get_context = get_context
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Generate the workflow preview."""
        args = PreviewWorkflowArgs(**kwargs)
        context = self._get_context()
        
        if not context:
            return {
                "success": False,
                "error": "Builder context not available",
            }
        
        # Check for design result
        if not context.state.design_result:
            return {
                "success": False,
                "error": "No workflow design to preview. Please generate a blueprint first.",
            }
        
        design = context.state.design_result
        validation = context.state.validation_result
        blueprint = design.blueprint_draft
        
        try:
            # Build the preview
            preview = {
                "status": "preview",
                "message": "Workflow ready for approval",
            }
            
            # Workflow info
            workflow_info = {
                "name": blueprint.get("name", "Untitled Workflow"),
                "description": blueprint.get("description", ""),
                "flow_summary": design.workflow_summary,
            }
            
            # Extract agents info
            agents = []
            for node in blueprint.get("nodes", []):
                node_type = node.get("type", "")
                if node_type in ["custom_agent_node", "$ref"]:
                    config = node.get("config", {})
                    agents.append({
                        "name": node.get("name", "Unknown"),
                        "rid": node.get("rid", ""),
                        "type": node_type,
                        "purpose": config.get("system_message", "")[:100] + "..." if len(config.get("system_message", "")) > 100 else config.get("system_message", ""),
                    })
            
            workflow_info["agents"] = agents
            workflow_info["agent_count"] = len(agents)
            
            # Created agents
            workflow_info["created_agents"] = design.created_agent_rids
            
            # Extract resources used
            resources_used = {
                "llms": [],
                "providers": [],
            }
            
            # Look for LLM references in nodes
            for node in blueprint.get("nodes", []):
                config = node.get("config", {})
                if config.get("llm"):
                    llm_ref = config["llm"]
                    if llm_ref not in resources_used["llms"]:
                        resources_used["llms"].append(llm_ref)
                if config.get("provider"):
                    provider_ref = config["provider"]
                    if provider_ref not in resources_used["providers"]:
                        resources_used["providers"].append(provider_ref)
            
            workflow_info["resources_used"] = resources_used
            
            # Validation status
            if validation:
                workflow_info["validation"] = {
                    "is_valid": validation.is_valid,
                    "warning_count": len(validation.validation_warnings),
                    "warnings": [w.get("message", "") for w in validation.validation_warnings[:3]],
                    "suggestions": validation.suggestions,
                }
            
            preview["workflow"] = workflow_info
            
            # Actions available
            preview["actions"] = [
                {
                    "id": "approve_and_save",
                    "label": "Approve and Save Workflow",
                    "description": "Save this workflow to your library",
                },
                {
                    "id": "modify",
                    "label": "Request Changes",
                    "description": "Ask the builder to modify the workflow",
                },
                {
                    "id": "cancel",
                    "label": "Cancel",
                    "description": "Discard this workflow",
                },
            ]
            
            # Include full blueprint if requested
            if args.include_full_blueprint:
                preview["blueprint_draft"] = blueprint
            
            # Format as readable text for the LLM to present
            readable_preview = self._format_readable_preview(preview)
            preview["readable_preview"] = readable_preview
            
            return {
                "success": True,
                "preview": preview,
                "message": readable_preview,
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error generating preview: {str(e)}",
            }
    
    def _format_readable_preview(self, preview: Dict[str, Any]) -> str:
        """Format the preview as readable text."""
        workflow = preview.get("workflow", {})
        
        lines = [
            "=" * 60,
            "📋 WORKFLOW PREVIEW",
            "=" * 60,
            "",
            f"**Name**: {workflow.get('name', 'Untitled')}",
            "",
            f"**Description**: {workflow.get('description', 'No description')}",
            "",
            f"**Flow**: {workflow.get('flow_summary', 'N/A')}",
            "",
        ]
        
        # Agents section
        agents = workflow.get("agents", [])
        if agents:
            lines.append(f"**Agents** ({len(agents)}):")
            for agent in agents:
                lines.append(f"  - {agent.get('name', 'Unknown')}")
                if agent.get("purpose"):
                    lines.append(f"    Purpose: {agent.get('purpose')}")
            lines.append("")
        
        # Created agents
        created = workflow.get("created_agents", [])
        if created:
            lines.append(f"**Newly Created Agents**: {', '.join(created)}")
            lines.append("")
        
        # Resources
        resources = workflow.get("resources_used", {})
        if resources.get("llms") or resources.get("providers"):
            lines.append("**Resources Used**:")
            if resources.get("llms"):
                lines.append(f"  - LLMs: {', '.join(str(l) for l in resources['llms'])}")
            if resources.get("providers"):
                lines.append(f"  - Providers: {', '.join(str(p) for p in resources['providers'])}")
            lines.append("")
        
        # Validation
        validation = workflow.get("validation", {})
        if validation:
            status = "✅ Valid" if validation.get("is_valid") else "❌ Invalid"
            lines.append(f"**Validation**: {status}")
            if validation.get("warnings"):
                lines.append("  Warnings:")
                for warning in validation["warnings"]:
                    lines.append(f"    ⚠️ {warning}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append("**Available Actions**:")
        lines.append("  1. approve_and_save - Save this workflow")
        lines.append("  2. modify - Request changes")
        lines.append("  3. cancel - Discard")
        lines.append("=" * 60)
        
        return "\n".join(lines)


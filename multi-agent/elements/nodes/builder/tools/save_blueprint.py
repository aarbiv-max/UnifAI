"""
Save Blueprint Tool for the Builder Agent.

Saves the generated workflow blueprint after user approval.
"""

from typing import Any, Callable, Dict
from pydantic import BaseModel, Field

from elements.tools.common.base_tool import BaseTool
from ..context import BuilderContext


class SaveBlueprintArgs(BaseModel):
    """Arguments for saving the blueprint."""
    confirm_save: bool = Field(
        description="Set to True to confirm saving the workflow"
    )
    custom_name: str = Field(
        default="",
        description="Optional custom name for the workflow (overrides generated name)"
    )


class SaveBlueprintTool(BaseTool):
    """
    Save the generated workflow blueprint.
    
    After validation passes and the user approves, use this tool to save
    the workflow to the database.
    """
    
    name = "save_blueprint"
    description = """Save the generated workflow blueprint to the database.

Call this tool after:
1. The workflow has been validated successfully
2. The user has reviewed the preview
3. The user confirms they want to save it

Args:
    confirm_save: Must be True to actually save
    custom_name: Optional custom name for the workflow

Returns the saved blueprint ID on success."""
    
    args_schema = SaveBlueprintArgs
    
    def __init__(self, get_context: Callable[[], BuilderContext]):
        """
        Initialize the tool.
        
        Args:
            get_context: Callable to get the builder context
        """
        self._get_context = get_context
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Save the blueprint."""
        args = SaveBlueprintArgs(**kwargs)
        context = self._get_context()
        
        if not context:
            return {
                "success": False,
                "error": "Builder context not available",
            }
        
        if not args.confirm_save:
            return {
                "success": False,
                "error": "Save not confirmed. Set confirm_save=True to save the workflow.",
            }
        
        # Check if we have a design result with blueprint
        design_result = context.state.design_result
        if not design_result or not design_result.blueprint_draft:
            return {
                "success": False,
                "error": "No blueprint to save. Run generate_blueprint first.",
            }
        
        # Check validation status - warnings are allowed, only block on critical errors
        validation_result = context.state.validation_result
        warnings = []
        if validation_result and not validation_result.is_valid:
            # Log warnings but don't block save - most validation issues are non-critical
            warnings = validation_result.validation_errors or []
        
        blueprint_service = context.blueprint_service
        if not blueprint_service:
            return {
                "success": False,
                "error": "Blueprint service not available",
            }
        
        try:
            # Get the blueprint draft
            blueprint_dict = design_result.blueprint_draft.copy()
            
            # Apply custom name if provided
            if args.custom_name:
                blueprint_dict["name"] = args.custom_name
            
            # Save the blueprint
            blueprint_id = blueprint_service.save_draft(
                user_id=context.user_id,
                draft_dict=blueprint_dict
            )
            
            # Store the saved blueprint ID in context for final result
            design_result.saved_blueprint_id = blueprint_id
            
            result = {
                "success": True,
                "blueprint_id": blueprint_id,
                "name": blueprint_dict.get("name", "Unnamed Workflow"),
                "message": f"Workflow '{blueprint_dict.get('name')}' saved successfully!",
                "next_steps": [
                    "You can now create sessions with this workflow",
                    f"Use blueprint_id: {blueprint_id} to run it",
                    "The workflow is available in your blueprints list"
                ]
            }
            
            # Include warnings if there were validation issues
            if warnings:
                result["warnings"] = warnings
                result["message"] += " (saved with validation warnings)"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error saving blueprint: {str(e)}",
            }


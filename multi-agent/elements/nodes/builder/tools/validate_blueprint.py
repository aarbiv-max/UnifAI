"""
Validate Blueprint Tool for the Builder Agent.

Validates the generated workflow blueprint.
"""

from typing import Any, Callable, Dict
from pydantic import BaseModel, Field

from elements.tools.common.base_tool import BaseTool
from ..context import BuilderContext, ValidationResult


class ValidateBlueprintArgs(BaseModel):
    """Arguments for validating a blueprint."""
    timeout_seconds: float = Field(
        default=10.0,
        description="Timeout for validation checks"
    )


class ValidateBlueprintTool(BaseTool):
    """
    Validate the generated workflow blueprint.
    
    Runs schema validation and element validators to ensure
    the blueprint is valid before saving.
    """
    
    name = "validate_blueprint"
    description = """Validate the generated workflow blueprint.

Checks:
- Schema validation (all required fields present)
- Resource references are valid
- Element-specific validation (LLM connectivity, provider health, etc.)

Returns validation results with any errors or warnings.
If validation fails, you may need to fix issues and try again."""
    
    args_schema = ValidateBlueprintArgs
    
    def __init__(self, get_context: Callable[[], BuilderContext]):
        """
        Initialize the tool.
        
        Args:
            get_context: Callable to get the builder context
        """
        self._get_context = get_context
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Validate the blueprint."""
        args = ValidateBlueprintArgs(**kwargs)
        context = self._get_context()
        
        if not context:
            return {
                "success": False,
                "is_valid": False,
                "error": "Builder context not available",
            }
        
        # Check if we have a blueprint to validate
        if not context.state.design_result or not context.state.design_result.blueprint_draft:
            return {
                "success": False,
                "is_valid": False,
                "error": "No blueprint to validate. Please generate a blueprint first.",
            }
        
        blueprint = context.state.design_result.blueprint_draft
        
        try:
            errors = []
            warnings = []
            suggestions = []
            
            # Basic structure validation
            if not blueprint.get("name"):
                errors.append({
                    "field": "name",
                    "message": "Workflow name is required",
                })
            
            if not blueprint.get("plan"):
                errors.append({
                    "field": "plan",
                    "message": "Workflow plan is required",
                })
            
            # Check for required nodes
            nodes = blueprint.get("nodes", [])
            node_rids = {n.get("rid") for n in nodes}
            
            has_user_question = any(
                n.get("type") == "user_question_node" for n in nodes
            )
            has_final_answer = any(
                n.get("type") == "final_answer_node" for n in nodes
            )
            
            if not has_user_question:
                errors.append({
                    "field": "nodes",
                    "message": "Workflow must include a user_question_node",
                })
            
            if not has_final_answer:
                errors.append({
                    "field": "nodes",
                    "message": "Workflow must include a final_answer_node",
                })
            
            # Check plan references valid nodes
            plan = blueprint.get("plan", [])
            for step in plan:
                node_ref = step.get("node")
                if node_ref:
                    # $ref: references point to external resources (resolved at runtime)
                    if node_ref.startswith("$ref:"):
                        # External reference - will be resolved from resource registry
                        continue
                    elif node_ref not in node_rids:
                        errors.append({
                            "field": f"plan.{step.get('uid')}",
                            "message": f"Step references unknown node: {node_ref}",
                        })
            
            # Check for LLM references in agent nodes
            for node in nodes:
                if node.get("type") in ["custom_agent_node", "orchestrator_node"]:
                    config = node.get("config", {})
                    if not config.get("llm"):
                        warnings.append({
                            "field": f"nodes.{node.get('rid')}",
                            "message": f"Agent node '{node.get('name')}' has no LLM configured",
                        })
            
            # Use blueprint service validation if available
            if context.blueprint_service:
                try:
                    validation_result = context.blueprint_service.validate_draft(
                        draft_dict=blueprint,
                        timeout_seconds=args.timeout_seconds,
                    )
                    
                    if not validation_result.is_valid:
                        for rid, elem_result in validation_result.element_results.items():
                            if not elem_result.is_valid:
                                for msg in elem_result.messages:
                                    if msg.severity.value == "error":
                                        errors.append({
                                            "field": rid,
                                            "message": msg.message,
                                        })
                                    elif msg.severity.value == "warning":
                                        warnings.append({
                                            "field": rid,
                                            "message": msg.message,
                                        })
                except Exception as e:
                    warnings.append({
                        "field": "validation",
                        "message": f"Full validation unavailable: {str(e)}",
                    })
            
            # Generate suggestions
            if warnings:
                suggestions.append("Consider addressing the warnings for a more robust workflow")
            
            if len(nodes) > 5:
                suggestions.append("Large workflow detected. Consider breaking into smaller sub-workflows for maintainability")
            
            is_valid = len(errors) == 0
            
            # Update context state (don't advance phase - node manages that)
            validation = ValidationResult(
                is_valid=is_valid,
                validation_errors=errors,
                validation_warnings=warnings,
                suggestions=suggestions,
            )
            context.state.validation_result = validation
            
            return {
                "success": True,
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions,
                "message": "Validation passed" if is_valid else f"Validation failed with {len(errors)} error(s)",
            }
            
        except Exception as e:
            return {
                "success": False,
                "is_valid": False,
                "error": f"Error during validation: {str(e)}",
            }


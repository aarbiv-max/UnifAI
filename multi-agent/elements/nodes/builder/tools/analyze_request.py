"""
Analyze Request Tool for the Builder Agent.

Records the analysis of the user's workflow request.
"""

from typing import Any, Callable, Dict, List
from pydantic import BaseModel, Field

from elements.tools.common.base_tool import BaseTool
from ..context import BuilderContext, AnalysisResult


class AnalyzeRequestArgs(BaseModel):
    """Arguments for recording request analysis."""
    intent: str = Field(
        description="The main goal/intent of the workflow (e.g., 'Search Jira and summarize findings')"
    )
    required_capabilities: List[str] = Field(
        description="List of required capabilities/integrations (e.g., ['jira', 'confluence', 'slack'])"
    )
    needs_orchestrator: bool = Field(
        description="Whether multiple agents need coordination (True if 2+ specialized agents needed)"
    )
    suggested_agent_count: int = Field(
        default=1,
        description="Suggested number of agents for this workflow"
    )
    analysis_notes: str = Field(
        default="",
        description="Additional notes or reasoning about the analysis"
    )


class AnalyzeRequestTool(BaseTool):
    """
    Record the analysis of the user's workflow request.
    
    This tool should be called after analyzing the user's request
    to record the extracted requirements for subsequent phases.
    """
    
    name = "analyze_request"
    description = """Record your analysis of the user's workflow request.

After analyzing what the user wants to build, use this tool to record:
- The main intent/goal of the workflow
- Required capabilities (external systems like jira, confluence, slack, etc.)
- Whether an orchestrator is needed (for multi-agent coordination)
- Suggested number of agents

This information will guide the resource search and design phases.

Example:
    analyze_request(
        intent="Search Jira tickets and summarize findings with Confluence context",
        required_capabilities=["jira", "confluence"],
        needs_orchestrator=True,
        suggested_agent_count=2,
        analysis_notes="User needs to query both systems and merge results"
    )"""
    
    args_schema = AnalyzeRequestArgs
    
    def __init__(self, get_context: Callable[[], BuilderContext]):
        """
        Initialize the tool.
        
        Args:
            get_context: Callable to get the builder context
        """
        self._get_context = get_context
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Record the analysis results."""
        args = AnalyzeRequestArgs(**kwargs)
        context = self._get_context()
        
        if not context:
            return {
                "success": False,
                "error": "Builder context not available",
            }
        
        try:
            # Create analysis result
            analysis = AnalysisResult(
                user_request=context.state.user_id,  # Will be set properly
                intent=args.intent,
                required_capabilities=args.required_capabilities,
                needs_orchestrator=args.needs_orchestrator,
                suggested_agent_count=args.suggested_agent_count,
                raw_analysis=args.analysis_notes,
            )
            
            # Store in context (don't advance phase - node manages that)
            context.state.analysis = analysis
            
            return {
                "success": True,
                "phase_complete": True,  # Signal that this phase is done
                "intent": args.intent,
                "required_capabilities": args.required_capabilities,
                "needs_orchestrator": args.needs_orchestrator,
                "suggested_agent_count": args.suggested_agent_count,
                "message": f"Analysis recorded successfully. "
                          f"Intent: {args.intent}. "
                          f"Required capabilities: {', '.join(args.required_capabilities)}. "
                          f"Orchestrator needed: {args.needs_orchestrator}.",
                "next_action": "PHASE COMPLETE - Analysis is done. Do NOT call this tool again. Proceed to summarize the analysis and complete this phase.",
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error recording analysis: {str(e)}",
            }


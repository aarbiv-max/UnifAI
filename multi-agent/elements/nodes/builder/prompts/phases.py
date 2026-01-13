"""
Phase-specific prompts and guidance for the Builder Agent.

Contains both static guidance (for PhaseDefinition) and dynamic prompt builders
(for runtime context injection).
"""

from typing import List

# =============================================================================
# STATIC PHASE GUIDANCE (Used in PhaseDefinition)
# =============================================================================

ANALYZE_PHASE_GUIDANCE = """PHASE: ANALYZE - Parse and understand the user's workflow requirements.

YOUR ROLE IN THIS PHASE:
- Analyze the user's request to understand their workflow needs
- Identify ALL required capabilities (external systems, agent roles)
- Determine if an orchestrator is needed for multi-agent coordination
- Record your analysis using the analyze_request tool

ANALYSIS CHECKLIST:
1. Intent: What is the main goal of this workflow?
2. Required Capabilities: External systems (jira, confluence, slack) AND agent roles (sales, support)
3. Agent Count: How many specialized agents are needed?
4. Orchestration: Does this require coordination between multiple agents?

IMPORTANT RULES:
- If the user mentions ANY agent type (like "sales agent"), include that role in required_capabilities
- Call analyze_request exactly ONCE with all your findings
- After the tool returns success, this phase is complete - do NOT call the tool again

Example tool call:
analyze_request(
    intent="Search Jira tickets and summarize with Confluence context",
    required_capabilities=["jira", "confluence"],
    needs_orchestrator=True,
    suggested_agent_count=2,
    analysis_notes="User needs multi-source knowledge retrieval"
)"""


SEARCH_PHASE_GUIDANCE = """PHASE: SEARCH - Find available resources in the user's account.

YOUR ROLE IN THIS PHASE:
- Search for available LLMs (MANDATORY - at least one required)
- Find providers/MCPs that match the required capabilities
- Discover existing agents that could be reused (both Custom Agents and A2A Agents)

SEARCH WORKFLOW:
1. Call search_resources tool with capability filter from analysis
2. Review results to understand what's available
3. Note any missing capabilities for the design phase

AGENT INVENTORIES:
- Custom Agents: Local agents with LLM and optional provider
- A2A Agents: Remote agents that delegate to external A2A-compatible services

IMPORTANT RULES:
- LLMs are MANDATORY - workflow cannot work without at least one
- Match providers to required capabilities (e.g., Jira provider for Jira tasks)
- Identify existing agents (custom or A2A) that can be reused instead of creating duplicates
- A2A agents are specialized remote agents - prefer them when they match required capabilities
- Call search_resources exactly ONCE"""


DESIGN_PHASE_GUIDANCE = """PHASE: DESIGN - Generate the workflow blueprint.

YOUR ROLE IN THIS PHASE:
- Use available resources to design the workflow
- Call generate_blueprint with workflow name and description
- The tool automatically reuses existing agents and creates new ones from providers

DESIGN WORKFLOW:
1. Review available resources from search phase
2. Call generate_blueprint with descriptive name and description
3. The tool handles agent reuse/creation and blueprint structure

AGENT PRIORITY:
1. First: Reuse existing A2A agents (specialized remote agents)
2. Second: Reuse existing custom agents
3. Third: Create new agents from matched providers
4. Last: Create LLM-only agents for remaining capabilities

IMPORTANT RULES:
- The tool automatically handles agent reuse and creation - do NOT create agents separately
- A2A agents are self-contained (no LLM needed) and are reused as-is
- Custom agents from search results will be reused with their configuration
- Call generate_blueprint exactly ONCE
- The blueprint will include user_question_node, orchestrator (if needed), agents, and final_answer_node

Example tool call:
generate_blueprint(
    workflow_name="Jira Search Workflow",
    workflow_description="Search Jira tickets and provide summaries"
)"""


VALIDATE_PHASE_GUIDANCE = """PHASE: VALIDATE - Validate, preview and save the workflow.

YOUR ROLE IN THIS PHASE:
- Validate the generated blueprint for errors
- Preview the workflow structure for user review
- Save the blueprint to the database

VALIDATION WORKFLOW:
1. Call validate_blueprint to check for any issues
2. Call preview_workflow to show the workflow structure
3. Call save_blueprint with confirm_save=True to save the workflow

IMPORTANT RULES:
- Validation warnings are informational only - ALWAYS proceed to save
- The workflow should be saved even if there are minor validation issues
- Only fatal errors (like missing required fields) should block saving
- After saving, report the blueprint_id to the user"""


# =============================================================================
# DYNAMIC PROMPT BUILDERS (For runtime context injection)
# =============================================================================

def build_analyze_prompt(user_request: str) -> str:
    """
    Build the prompt for the ANALYZE phase.
    
    Args:
        user_request: The user's original workflow request
        
    Returns:
        Formatted prompt string with user request context
    """
    return f"""## Phase 1: Analyze Request

Please analyze this workflow request and identify the requirements.

**User Request:**
{user_request}

**Your Analysis Should Include:**
1. **Intent**: What is the main goal of this workflow?
2. **Required Capabilities**: ALL capabilities needed, including:
   - External systems/tools (e.g., jira, confluence, slack, email)
   - Agent roles mentioned by the user (e.g., sales, support, analyst)
   - Include EVERY distinct capability or role mentioned in the request
3. **Agent Count**: How many specialized agents are needed?
4. **Orchestration**: Does this require an orchestrator to coordinate multiple agents?

**IMPORTANT**: If the user mentions ANY agent type (like "sales agent", "support agent"), include that role in required_capabilities (e.g., "sales", "support").

Think through this carefully, then use the `analyze_request` tool ONCE to record your findings.

**IMPORTANT:** Call `analyze_request` exactly ONCE with all your findings. After the tool returns success, this phase is complete - do NOT call the tool again.

Example:
```
analyze_request(
    intent="Search Jira tickets and summarize with Confluence context",
    required_capabilities=["jira", "confluence"],
    needs_orchestrator=True,
    suggested_agent_count=2,
    analysis_notes="User needs multi-source knowledge retrieval"
)
```

Analyze the request now and call the tool ONCE."""


def build_search_prompt(capabilities: List[str]) -> str:
    """
    Build the prompt for the SEARCH phase.
    
    Args:
        capabilities: List of required capabilities from analysis
        
    Returns:
        Formatted prompt string with capabilities context
    """
    cap_str = ", ".join(capabilities) if capabilities else "general purpose"
    
    return f"""## Phase 2: Search Resources

Now search for available resources in the user's account.

**Required Capabilities:** {cap_str}

Use the `search_resources` tool to find:
1. **LLMs** (MANDATORY - at least one is required)
2. **Providers/MCPs** that match the required capabilities
3. **Existing Custom Agents** that could be reused
4. **Existing A2A Agents** (remote agents) that match capabilities

**Agent Types:**
- Custom Agents: Local agents using your LLM and providers
- A2A Agents: Remote agents that delegate to external services (specialized, no LLM needed)

Call the search_resources tool now."""


def build_design_prompt(
    llm_info: str,
    provider_count: int,
    agent_info: str,
    needs_orchestrator: bool
) -> str:
    """
    Build the prompt for the DESIGN phase.
    
    Args:
        llm_info: Description of available LLM
        provider_count: Number of available providers
        agent_info: Description of existing agents
        needs_orchestrator: Whether orchestrator is needed
        
    Returns:
        Formatted prompt string with resource context
    """
    return f"""## Phase 3: Design Workflow

Based on the search results, generate the workflow blueprint.

**Available Resources:**
- {llm_info}
- Providers: {provider_count}
- {agent_info}

**Workflow Requirements:**
- Needs Orchestrator: {needs_orchestrator}

**Your Task:**
Call `generate_blueprint` ONCE with:
- workflow_name: A descriptive name for the workflow  
- workflow_description: What the workflow does

**Agent Handling (Automatic):**
1. A2A Agents are reused first (specialized remote agents, no local LLM needed)
2. Custom Agents are reused second (with their existing configuration)
3. New agents are created from matched providers if needed
4. LLM-only agents are created for remaining capabilities

**IMPORTANT:** 
- The tool automatically handles agent reuse and creation - you do NOT need to create agents separately
- All existing agents (custom and A2A) from search results will be reused when they match capabilities
- Call `generate_blueprint` exactly ONCE

Example:
```
generate_blueprint(
    workflow_name="Jira Search Workflow",
    workflow_description="Search Jira tickets and provide summaries"
)
```

Generate the blueprint now."""


def build_validate_prompt() -> str:
    """
    Build the prompt for the VALIDATE phase.
    
    Returns:
        Formatted prompt string for validation phase
    """
    return """## Phase 4: Validate, Preview & Save

The workflow has been designed. Now:

1. Use `validate_blueprint` tool to check for any issues
2. Use `preview_workflow` tool to show the workflow structure
3. **ALWAYS use `save_blueprint` with confirm_save=True to save the workflow**

**IMPORTANT:** 
- Validation warnings are informational only - ALWAYS proceed to save the workflow
- The workflow should be saved even if there are minor validation issues
- Only fatal errors (like missing required fields) should block saving
- After saving, report the blueprint_id to the user

Call validate_blueprint now, then preview_workflow, then save_blueprint."""

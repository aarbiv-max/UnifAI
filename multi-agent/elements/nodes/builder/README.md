# 🏗️ Builder Agent Node

A multi-phase AI agent that automatically creates workflow blueprints based on natural language user requests.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [The 4 Phases](#the-4-phases)
4. [File Structure](#file-structure)
5. [Core Classes](#core-classes)
6. [Tools](#tools)
7. [Helper Classes](#helper-classes)
8. [Data Models](#data-models)
9. [Prompts System](#prompts-system)
10. [Service Protocols](#service-protocols)
11. [Exception Handling](#exception-handling)
12. [Frontend Integration](#frontend-integration)
13. [Streaming Events](#streaming-events)
14. [Generated Blueprint Example](#generated-blueprint-example)
15. [Usage](#usage)
16. [Configuration](#configuration)

---

## Overview

The **Builder Agent** enables users to create multi-agent workflows through natural conversation. Instead of manually configuring nodes, connections, and orchestration patterns, users simply describe what they want:

> "Create a workflow to search Jira tickets and find related Confluence pages"

The builder then:
1. **Analyzes** the request to identify required capabilities
2. **Searches** the user's inventory for available resources
3. **Designs** a complete workflow with appropriate agents
4. **Validates** and saves the blueprint to the database

### Key Features

- **Natural Language Input**: Describe workflows in plain English
- **Resource Discovery**: Automatically finds LLMs, providers, and existing agents
- **Smart Agent Reuse**: Reuses existing agents when appropriate
- **Orchestrator Pattern**: Automatically adds orchestrator for multi-agent workflows
- **Real-time Streaming**: Sends phase progress events to the frontend
- **Inventory Integration**: Creates new agent resources in user's inventory

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               SMART BUILDER FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────────┐
                                    │      USER       │
                                    │   "Create a     │
                                    │   Jira workflow"│
                                    └────────┬────────┘
                                             │
                             ┌───────────────▼───────────────┐
                             │     FRONTEND (React)          │
                             │   SmartBuilderPanel.tsx       │
                             │   ───────────────────────     │
                             │   • Check builder agent       │
                             │   • Create session            │
                             │   • Execute with streaming    │
                             │   • Display phase progress    │
                             └───────────────┬───────────────┘
                                             │ HTTP POST (stream: true)
                                             │ /sessions/user.session.execute
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                               BACKEND (Flask)                                     │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────┐    │
│   │                            BuilderNode                                   │    │
│   │                       (Multi-Phase Agent)                                │    │
│   │                                                                          │    │
│   │  Inherits: BaseNode, LlmCapableMixin, AgentCapableMixin,                │    │
│   │            WorkloadCapableMixin, IEMCapableMixin                         │    │
│   └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                       │                                           │
│   ╔═══════════════════════════════════════════════════════════════════════╗      │
│   ║                      4-PHASE EXECUTION                                 ║      │
│   ╠═══════════════════════════════════════════════════════════════════════╣      │
│   ║                                                                        ║      │
│   ║  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐ ║      │
│   ║  │  PHASE 1   │───▶│  PHASE 2   │───▶│  PHASE 3   │───▶│  PHASE 4   │ ║      │
│   ║  │  ANALYZE   │    │  SEARCH    │    │  DESIGN    │    │  VALIDATE  │ ║      │
│   ║  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘    └─────┬──────┘ ║      │
│   ║        │                 │                 │                 │        ║      │
│   ║        ▼                 ▼                 ▼                 ▼        ║      │
│   ║  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  ║      │
│   ║  │AnalyzeRequest│ │SearchResources│ │GenerateBlue- │ │ValidateBlue- │  ║      │
│   ║  │    Tool      │ │    Tool      │ │  print Tool  │ │  print Tool  │  ║      │
│   ║  └──────────────┘ └──────────────┘ └──────────────┘ ├──────────────┤  ║      │
│   ║                                                      │PreviewWorkflow│  ║      │
│   ║                                                      ├──────────────┤  ║      │
│   ║                                                      │SaveBlueprint │  ║      │
│   ║                                                      │    Tool      │  ║      │
│   ║                                                      └──────────────┘  ║      │
│   ╚═══════════════════════════════════════════════════════════════════════╝      │
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────┐    │
│   │                           SERVICES (Lazy Loaded)                         │    │
│   │                                                                          │    │
│   │   ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐       │    │
│   │   │ResourcesService │  │BlueprintService │  │ CatalogService    │       │    │
│   │   │                 │  │                 │  │                   │       │    │
│   │   │• find_resources │  │• save_draft     │  │• get_element_spec │       │    │
│   │   │• create         │  │• validate_draft │  │• list_elements    │       │    │
│   │   └─────────────────┘  └─────────────────┘  └───────────────────┘       │    │
│   └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## The 4 Phases

### Phase 1: ANALYZE

**Purpose**: Parse and understand the user's workflow requirements.

**Tool**: `AnalyzeRequestTool`

**What it does**:
1. LLM reads user request
2. Identifies intent (main goal)
3. Extracts required capabilities (jira, confluence, slack, etc.)
4. Determines if orchestrator is needed for multi-agent coordination
5. Suggests number of agents

**Input Arguments**:

```python
class AnalyzeRequestArgs(BaseModel):
    intent: str                        # Main goal of the workflow
    required_capabilities: List[str]   # e.g., ["jira", "confluence"]
    needs_orchestrator: bool           # True if 2+ specialized agents needed
    suggested_agent_count: int = 1     # Number of agents recommended
    analysis_notes: str = ""           # Additional reasoning
```

**Output**: `AnalysisResult` stored in `BuilderContext.state.analysis`

---

### Phase 2: SEARCH

**Purpose**: Find available resources in the user's account.

**Tool**: `SearchResourcesTool`

**What it searches for**:

| Resource Type | Purpose | Mandatory |
|---------------|---------|-----------|
| LLMs | Language models for reasoning | ✅ YES |
| Providers/MCPs | External tool access (Jira, Confluence) | Optional |
| Existing Agents | Agents that can be reused | Optional |
| Orchestrators | Existing orchestrator nodes | Optional |

**Matching Logic**:
- Provider matching is **STRICT**: Only matches if capability appears in provider name
- Agent matching: Checks agent name and attached provider
- Prevents false positives (e.g., Confluence won't match "jira")

**Output**: `ResourceSearchResult` stored in `BuilderContext.state.search_result`

```python
class ResourceSearchResult(BaseModel):
    llms: List[Dict[str, Any]] = []              # Available LLMs
    providers: List[Dict[str, Any]] = []          # Matched providers
    existing_nodes: List[Dict[str, Any]] = []     # Reusable agents
    existing_orchestrators: List[Dict[str, Any]] = []
    missing_capabilities: List[str] = []          # Capabilities not found
    has_required_llm: bool = False                # MUST be True to proceed
```

---

### Phase 3: DESIGN

**Purpose**: Generate the complete workflow blueprint.

**Tool**: `GenerateBlueprintTool`

**Key Components**:

1. **AgentBuilder Helper**: Creates agent nodes with priority:
   - First: Reuse existing agents matching capabilities
   - Second: Create new agents for matched providers
   - Third: Create LLM-only agents for remaining capabilities

2. **PlanBuilder Helper**: Creates execution plan:
   - Single agent: `user_question → agent → final_answer`
   - Orchestrated: `user_question → orchestrator → [agents] → final_answer`

**What gets generated**:
- `user_question_node` (entry point)
- `orchestrator_node` (if needed)
- Agent nodes (custom_agent_node)
- `final_answer_node` (exit point)
- `router_direct` condition (for orchestrator branching)
- Execution plan

**Output**: `DesignResult` stored in `BuilderContext.state.design_result`

```python
class DesignResult(BaseModel):
    blueprint_draft: Dict[str, Any] = {}    # Full blueprint JSON
    created_agent_rids: List[str] = []      # RIDs of newly created agents
    workflow_summary: str = ""              # Human-readable flow description
    plan_description: str = ""              # Plan explanation
    saved_blueprint_id: str = ""            # Populated after save
    agents_created: int = 0                 # New agents created
    agents_reused: int = 0                  # Existing agents reused
    uses_orchestrator: bool = False         # Whether orchestrator is used
```

---

### Phase 4: VALIDATE & SAVE

**Purpose**: Validate, preview, and save the workflow.

**Tools**:

| Tool | Description |
|------|-------------|
| `ValidateBlueprintTool` | Checks structure, node references, LLM config |
| `PreviewWorkflowTool` | Generates human-readable summary |
| `SaveBlueprintTool` | Persists blueprint to database |

**Validation Checks**:
- Workflow name exists
- Plan is defined
- `user_question_node` present
- `final_answer_node` present
- All plan step references are valid
- All agent nodes have LLM configured

**Output**: `blueprint_id` returned to frontend

---

## File Structure

```
builder/
├── __init__.py                 # Module exports
├── builder_node.py             # Main BuilderNode class (618 lines)
├── builder_node_factory.py     # Factory for creating BuilderNode instances
├── config.py                   # BuilderNodeConfig settings
├── exceptions.py               # Custom exceptions hierarchy
├── identifiers.py              # BuilderPhase enum, Identifier, META
├── protocols.py                # Service protocol interfaces
├── validator.py                # Element validator
│
├── context/
│   ├── __init__.py
│   └── builder_context.py      # BuilderContext, BuilderState, Result models
│
├── phases/
│   ├── __init__.py
│   └── phase_provider.py       # BuilderPhaseProvider using PhaseDefinition
│
├── prompts/
│   ├── __init__.py             # Exports all prompts
│   ├── system.py               # BUILDER_SYSTEM_MESSAGE
│   └── phases.py               # Phase-specific guidance & dynamic prompts
│
├── spec/
│   ├── __init__.py
│   └── spec.py                 # Element specification for catalog
│
└── tools/
    ├── __init__.py             # Tool exports
    ├── analyze_request.py      # Phase 1 tool
    ├── search_resources.py     # Phase 2 tool
    ├── generate_blueprint.py   # Phase 3 tool
    ├── validate_blueprint.py   # Phase 4 tool
    ├── preview_workflow.py     # Phase 4 tool
    ├── save_blueprint.py       # Phase 4 tool
    │
    └── helpers/
        ├── __init__.py
        ├── agent_builder.py    # AgentBuilder class
        └── plan_builder.py     # PlanBuilder class
```

---

## Core Classes

### BuilderNode

The main orchestrator class that runs the 4-phase workflow.

```python
class BuilderNode(
    WorkloadCapableMixin,     # Task handling
    IEMCapableMixin,          # Internal event management
    AgentCapableMixin,        # Agent execution (run_agent, create_strategy)
    LlmCapableMixin,          # LLM access
    BaseNode                  # Base functionality, streaming
):
    """Multi-phase agent that creates workflows based on user requirements."""
    
    def __init__(
        self,
        *,
        llm: Any,                           # Required: LLM for reasoning
        resources_service: Any = None,       # Optional: lazy loaded
        blueprint_service: Any = None,       # Optional: lazy loaded
        catalog_service: Any = None,         # Optional: lazy loaded
        validation_service: Any = None,      # Optional: lazy loaded
        system_message: str = "",            # Custom instructions
        max_rounds: int = 20,                # Max LLM iterations
        **kwargs
    )
```

**Key Methods**:

```python
def run(self, state: StateView) -> StateView:
    """Entry point - processes incoming packets."""
    self.process_packets(state)
    return state

def handle_task_packet(self, packet) -> None:
    """Handle incoming task - runs all phases."""
    # 1. Extract task
    # 2. Initialize BuilderContext
    # 3. Build phase tools
    # 4. Create BuilderPhaseProvider
    # 5. Run _run_builder_phases()
    # 6. Create AgentResult
    # 7. Route response
    # 8. Cleanup (finally block)

def _run_builder_phases(self, user_request: str) -> Dict[str, Any]:
    """Sequential execution of all 4 phases."""
    # For each phase:
    #   1. Stream "started" event
    #   2. Call _run_phase()
    #   3. Check success
    #   4. Stream "complete" or "failed" event
    #   5. Update metadata
    
def _run_phase(
    self,
    phase: BuilderPhase,
    user_request: str,
    conversation_history: List[ChatMessage],
    phase_prompt: str,
) -> Dict[str, Any]:
    """Execute a single phase with its tools and prompt."""
    # 1. Get phase tools
    # 2. Build messages with context
    # 3. Create ReAct strategy
    # 4. Run agent
    # 5. Update conversation history
```

---

### BuilderContext

Holds all state and services for the builder execution.

```python
class BuilderContext:
    """Context manager for the builder agent."""
    
    def __init__(
        self,
        user_id: str,
        thread_id: str,
        resources_service: Optional[ResourcesServiceProtocol] = None,
        blueprint_service: Optional[BlueprintServiceProtocol] = None,
        catalog_service: Optional[CatalogServiceProtocol] = None,
        validation_service: Optional[ValidationServiceProtocol] = None,
    ):
        self._state = BuilderState(user_id=user_id, thread_id=thread_id)
        # Store services...
    
    @property
    def state(self) -> BuilderState:
        """Get current builder state."""
        return self._state
    
    def set_analysis_result(self, result: AnalysisResult) -> None:
        """Set analysis result and advance phase."""
        self._state.analysis = result
        self._state.advance_phase()
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary for LLM prompting."""
        # Returns dict with phase, user_id, analysis, resources, design, validation
```

---

### BuilderState

Accumulates results across all phases.

```python
@dataclass
class BuilderState:
    """Complete state for the builder agent across all phases."""
    
    # Current phase
    current_phase: BuilderPhase = BuilderPhase.ANALYZE
    
    # User context
    user_id: str = ""
    thread_id: str = ""
    
    # Phase results (populated as phases complete)
    analysis: Optional[AnalysisResult] = None
    search_result: Optional[ResourceSearchResult] = None
    design_result: Optional[DesignResult] = None
    validation_result: Optional[ValidationResult] = None
    
    def advance_phase(self) -> None:
        """Advance to the next phase in sequence."""
        phase_order = [ANALYZE, SEARCH, DESIGN, VALIDATE, COMPLETE]
        # Move to next phase...
```

---

### BuilderPhaseProvider

Provides phase-specific configuration using the PhaseDefinition pattern.

```python
class BuilderPhaseProvider:
    """Provides phase-specific context and tools."""
    
    def __init__(
        self,
        get_context: Callable[[], BuilderContext],
        tools_by_phase: Optional[Dict[BuilderPhase, List[BaseTool]]] = None,
        iteration_limits: Optional[Dict[BuilderPhase, int]] = None,
    ):
        self._phase_system = self._build_phase_system()
    
    def _build_phase_system(self) -> PhaseSystem:
        """Build complete phase system with PhaseDefinition objects."""
        phase_system = PhaseSystem(name="builder", description="...")
        
        # Add each phase with its guidance and tools
        phase_system.add_phase(PhaseDefinition(
            name=BuilderPhase.ANALYZE.value,
            description="Parse and understand requirements",
            tools=self._tools_by_phase.get(BuilderPhase.ANALYZE, []),
            guidance=ANALYZE_PHASE_GUIDANCE,
            max_iterations=5,
        ))
        # ... add other phases
        
        return phase_system
    
    def get_tools_for_phase(self, phase: BuilderPhase) -> List[BaseTool]:
        """Get tools available for a phase."""
        
    def get_context_messages(self) -> List[ChatMessage]:
        """Get context messages based on current state."""
```

---

## Tools

### AnalyzeRequestTool (Phase 1)

Records the LLM's understanding of the user's request.

```python
class AnalyzeRequestTool(BaseTool):
    name = "analyze_request"
    description = """Record your analysis of the user's workflow request..."""
    
    def run(self, **kwargs) -> Dict[str, Any]:
        args = AnalyzeRequestArgs(**kwargs)
        context = self._get_context()
        
        # Create AnalysisResult
        analysis = AnalysisResult(
            intent=args.intent,
            required_capabilities=args.required_capabilities,
            needs_orchestrator=args.needs_orchestrator,
            suggested_agent_count=args.suggested_agent_count,
            raw_analysis=args.analysis_notes,
        )
        
        # Store in context
        context.state.analysis = analysis
        
        return {
            "success": True,
            "phase_complete": True,
            "intent": args.intent,
            "required_capabilities": args.required_capabilities,
            "message": "Analysis recorded successfully.",
            "next_action": "PHASE COMPLETE - Do NOT call again.",
        }
```

---

### SearchResourcesTool (Phase 2)

Searches for available resources in the user's inventory.

```python
class SearchResourcesTool(BaseTool):
    name = "search_resources"
    
    def run(self, **kwargs) -> Dict[str, Any]:
        context = self._get_context()
        resources_service = context.resources_service
        user_id = context.user_id
        
        # Search for LLMs (mandatory)
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
        nodes, _ = resources_service.find_resources(
            user_id=user_id,
            category="nodes",
            limit=50
        )
        
        # Apply capability filter (STRICT matching on provider name)
        # ...
        
        # Create ResourceSearchResult
        result = ResourceSearchResult(
            llms=llm_list,
            providers=provider_list,
            existing_nodes=node_list,
            existing_orchestrators=orchestrator_list,
            has_required_llm=len(llm_list) > 0,
        )
        
        context.state.search_result = result
        return {"success": True, "phase_complete": True, ...}
```

---

### GenerateBlueprintTool (Phase 3)

Generates the complete workflow blueprint.

```python
class GenerateBlueprintTool(BaseTool):
    name = "generate_blueprint"
    
    def run(self, **kwargs) -> Dict[str, Any]:
        context = self._get_context()
        search_result = context.state.search_result
        analysis = context.state.analysis
        
        # Get first available LLM
        llm_rid = search_result.llms[0]["rid"]
        
        # Determine if orchestrator needed
        needs_orchestrator = (
            (analysis and analysis.needs_orchestrator) or 
            len(search_result.existing_nodes) > 1
        )
        
        # Use AgentBuilder helper
        agent_builder = AgentBuilder(
            llm_rid=llm_rid,
            resources_service=context.resources_service,
            user_id=context.user_id
        )
        agent_result = agent_builder.build_agents(
            existing_agents=search_result.existing_nodes,
            matched_providers=search_result.providers,
            required_capabilities=required_caps
        )
        
        # Initialize blueprint structure
        blueprint = {
            "name": args.workflow_name,
            "description": args.workflow_description,
            "nodes": [], "conditions": [], "plan": [], ...
        }
        
        # Add required nodes
        self._add_required_nodes(blueprint)  # user_question, final_answer
        
        # Add orchestrator if needed
        if needs_orchestrator:
            self._add_orchestrator_node(blueprint, llm_rid, ...)
        
        # Add agent nodes
        for agent_node in agent_result.agent_nodes:
            blueprint["nodes"].append(agent_node)
        
        # Build execution plan using PlanBuilder
        plan_builder = PlanBuilder()
        blueprint["plan"] = plan_builder.build_plan(
            agent_nodes=agent_result.agent_nodes,
            needs_orchestrator=needs_orchestrator,
            orchestrator_rid=orchestrator_rid
        )
        
        # Store in context
        context.state.design_result = DesignResult(
            blueprint_draft=blueprint,
            agents_created=agent_result.agents_created,
            agents_reused=agent_result.agents_reused,
            ...
        )
        
        return {"success": True, "phase_complete": True, "blueprint": blueprint}
```

---

### ValidateBlueprintTool (Phase 4)

Validates the generated blueprint.

```python
class ValidateBlueprintTool(BaseTool):
    name = "validate_blueprint"
    
    def run(self, **kwargs) -> Dict[str, Any]:
        context = self._get_context()
        blueprint = context.state.design_result.blueprint_draft
        
        errors = []
        warnings = []
        
        # Basic structure validation
        if not blueprint.get("name"):
            errors.append({"field": "name", "message": "Name required"})
        
        if not blueprint.get("plan"):
            errors.append({"field": "plan", "message": "Plan required"})
        
        # Check required nodes
        nodes = blueprint.get("nodes", [])
        has_user_question = any(n.get("type") == "user_question_node" for n in nodes)
        has_final_answer = any(n.get("type") == "final_answer_node" for n in nodes)
        
        if not has_user_question:
            errors.append(...)
        if not has_final_answer:
            errors.append(...)
        
        # Use blueprint service validation if available
        if context.blueprint_service:
            validation_result = context.blueprint_service.validate_draft(
                draft_dict=blueprint,
                timeout_seconds=args.timeout_seconds,
            )
            # Collect errors/warnings from service...
        
        is_valid = len(errors) == 0
        
        context.state.validation_result = ValidationResult(
            is_valid=is_valid,
            validation_errors=errors,
            validation_warnings=warnings,
        )
        
        return {"success": True, "is_valid": is_valid, "errors": errors}
```

---

### SaveBlueprintTool (Phase 4)

Persists the validated blueprint to the database.

```python
class SaveBlueprintTool(BaseTool):
    name = "save_blueprint"
    
    def run(self, **kwargs) -> Dict[str, Any]:
        args = SaveBlueprintArgs(**kwargs)
        context = self._get_context()
        
        if not args.confirm_save:
            return {"success": False, "error": "Save not confirmed"}
        
        blueprint_dict = context.state.design_result.blueprint_draft.copy()
        
        # Apply custom name if provided
        if args.custom_name:
            blueprint_dict["name"] = args.custom_name
        
        # Save using blueprint service
        blueprint_id = context.blueprint_service.save_draft(
            user_id=context.user_id,
            draft_dict=blueprint_dict
        )
        
        # Store ID for final result
        context.state.design_result.saved_blueprint_id = blueprint_id
        
        return {
            "success": True,
            "blueprint_id": blueprint_id,
            "name": blueprint_dict.get("name"),
            "message": f"Workflow '{blueprint_dict.get('name')}' saved!",
        }
```

---

## Helper Classes

### AgentBuilder

Handles agent node creation with smart reuse logic.

```python
@dataclass
class AgentBuildResult:
    agent_nodes: List[Dict[str, Any]] = field(default_factory=list)
    created_agent_rids: List[str] = field(default_factory=list)
    used_capabilities: Set[str] = field(default_factory=set)
    agents_created: int = 0
    agents_reused: int = 0

class AgentBuilder:
    """Builds agent nodes for workflow blueprints."""
    
    def __init__(self, llm_rid: str, resources_service: Any, user_id: str):
        self.llm_rid = llm_rid
        self.resources_service = resources_service
        self.user_id = user_id
    
    def build_agents(
        self,
        existing_agents: List[Dict],
        matched_providers: List[Dict],
        required_capabilities: Set[str]
    ) -> AgentBuildResult:
        """Build agent nodes with priority order."""
        result = AgentBuildResult()
        
        # Step 1: Add existing agents (reuse)
        self._add_existing_agents(existing_agents, result)
        
        # Step 2: Create agents for matched providers
        self._create_provider_agents(matched_providers, required_capabilities, result)
        
        # Step 3: Create LLM-only agents for remaining capabilities
        self._create_llm_only_agents(required_capabilities, result)
        
        return result
    
    def _create_or_get_agent(
        self,
        agent_name: str,
        system_message: str,
        provider_rid: Optional[str],
        fallback_rid: str
    ) -> Dict[str, Any]:
        """Create new agent resource or return inline config."""
        # Try to find existing agent with same name
        # If not found, create new resource in inventory
        # Return node config for blueprint
```

**Priority Order**:
1. **Reuse existing agents** matching required capabilities
2. **Create new agents** for providers matching capabilities (saved to inventory)
3. **Create LLM-only agents** for remaining capabilities (no provider)

---

### PlanBuilder

Constructs the execution plan for the workflow.

```python
class PlanBuilder:
    """Builds execution plans for workflow blueprints."""
    
    def build_plan(
        self,
        agent_nodes: List[Dict],
        needs_orchestrator: bool,
        orchestrator_rid: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Build execution plan."""
        plan = []
        
        # Always start with user input
        plan.append({"uid": "user_input", "node": "user_question_node_rid"})
        
        if needs_orchestrator and agent_nodes:
            # Orchestrator pattern
            plan.extend(self._build_orchestrator_plan(agent_nodes, orchestrator_rid))
        elif agent_nodes:
            # Single agent pattern
            plan.extend(self._build_single_agent_plan(agent_nodes[0]))
        else:
            # Direct flow (no agents)
            plan.extend(self._build_direct_flow())
        
        return plan
    
    def _build_orchestrator_plan(self, agent_nodes, orchestrator_rid) -> List[Dict]:
        """Build orchestrator pattern plan."""
        # orchestrator step with branches to each agent
        # agent steps
        # finalize step
    
    def _build_single_agent_plan(self, agent) -> List[Dict]:
        """Single agent: user_input -> agent -> finalize"""
    
    def build_workflow_summary(self, agent_nodes, needs_orchestrator) -> str:
        """Human-readable flow description."""
        # Returns: "user_question -> orchestrator -> [Agent1, Agent2] -> final_answer"
```

---

## Data Models

### AnalysisResult

```python
class AnalysisResult(BaseModel):
    user_request: str = ""
    intent: str = ""                          # Main goal
    required_capabilities: List[str] = []     # e.g., ["jira", "confluence"]
    needs_orchestrator: bool = False          # Multiple agents needed?
    suggested_agent_count: int = 1
    raw_analysis: str = ""                    # Additional notes
```

### ResourceSearchResult

```python
class ResourceSearchResult(BaseModel):
    llms: List[Dict[str, Any]] = []           # Available LLMs
    providers: List[Dict[str, Any]] = []      # Matched providers
    existing_nodes: List[Dict[str, Any]] = [] # Reusable agents
    existing_orchestrators: List[Dict[str, Any]] = []
    missing_capabilities: List[str] = []      # Not found
    has_required_llm: bool = False            # MUST be True
```

### DesignResult

```python
class DesignResult(BaseModel):
    blueprint_draft: Dict[str, Any] = {}      # Full blueprint JSON
    created_agent_rids: List[str] = []        # New agent RIDs
    workflow_summary: str = ""                # Human-readable flow
    plan_description: str = ""
    saved_blueprint_id: str = ""              # After save
    agents_created: int = 0
    agents_reused: int = 0
    uses_orchestrator: bool = False
```

### ValidationResult

```python
class ValidationResult(BaseModel):
    is_valid: bool = False
    validation_errors: List[Dict[str, Any]] = []
    validation_warnings: List[Dict[str, Any]] = []
    suggestions: List[str] = []
```

---

## Prompts System

### System Message (`prompts/system.py`)

```python
BUILDER_SYSTEM_MESSAGE = """You are a Workflow Builder Agent. Your role is to help users create multi-agent workflows.

## Your Capabilities
You can:
- Analyze user requests to understand workflow needs
- Search for available resources (LLMs, providers/MCPs, existing agents)
- Design workflows with appropriate agents and structure
- Validate workflows before presenting for approval

## Workflow Structure Rules
1. Every workflow MUST have:
   - A "user_question_node" as the entry point
   - A "final_answer_node" as the exit point

2. When multiple agents are needed:
   - Use an "orchestrator_node" to coordinate them
   - Flow: user_question -> orchestrator -> [agents] -> orchestrator -> final_answer

3. Each agent requires:
   - An LLM (mandatory)
   - A system_message
   - Optional: MCP provider

## Phase Approach
1. ANALYZE: Parse request, identify capabilities
2. SEARCH: Find available resources
3. DESIGN: Create blueprint
4. VALIDATE: Validate and save
"""
```

### Phase-Specific Prompts (`prompts/phases.py`)

**Static Guidance** (used in PhaseDefinition):

```python
ANALYZE_PHASE_GUIDANCE = """PHASE: ANALYZE - Parse user requirements.

YOUR ROLE:
- Analyze user's request to understand workflow needs
- Identify ALL required capabilities
- Determine if orchestrator needed
- Record analysis using analyze_request tool

IMPORTANT:
- Call analyze_request exactly ONCE
- After tool returns success, phase is complete
"""
```

**Dynamic Prompt Builders** (inject runtime context):

```python
def build_analyze_prompt(user_request: str) -> str:
    return f"""## Phase 1: Analyze Request
    
Please analyze this workflow request:

**User Request:**
{user_request}

**Your Analysis Should Include:**
1. Intent: Main goal of workflow
2. Required Capabilities: ALL needed (jira, confluence, sales, etc.)
3. Agent Count: How many specialized agents
4. Orchestration: Multiple agents need coordination?

Call `analyze_request` ONCE with your findings."""


def build_search_prompt(capabilities: List[str]) -> str:
    cap_str = ", ".join(capabilities)
    return f"""## Phase 2: Search Resources
    
Required Capabilities: {cap_str}

Use `search_resources` to find:
1. LLMs (MANDATORY)
2. Providers matching capabilities
3. Existing agents for reuse"""


def build_design_prompt(llm_info, provider_count, agent_info, needs_orchestrator) -> str:
    return f"""## Phase 3: Design Workflow

Available Resources:
- {llm_info}
- Providers: {provider_count}
- {agent_info}

Call `generate_blueprint` ONCE with workflow name and description."""


def build_validate_prompt() -> str:
    return """## Phase 4: Validate & Save

1. Call `validate_blueprint` to check issues
2. Call `preview_workflow` to show structure
3. Call `save_blueprint` with confirm_save=True"""
```

---

## Service Protocols

Defined in `protocols.py` using Python's `Protocol` for structural subtyping:

```python
@runtime_checkable
class ResourcesServiceProtocol(Protocol):
    def find_resources(
        self,
        user_id: str,
        category: Optional[str] = None,
        type: Optional[str] = None,
        **kwargs
    ) -> Tuple[List[Any], int]: ...
    
    def create(
        self,
        user_id: str,
        category: str,
        type: str,
        name: str,
        config: Dict[str, Any],
        **kwargs
    ) -> Any: ...


@runtime_checkable
class BlueprintServiceProtocol(Protocol):
    def validate_draft(
        self,
        draft_dict: Dict[str, Any],
        timeout_seconds: float = 10.0,
    ) -> Any: ...
    
    def save_draft(
        self,
        *,
        user_id: str,
        draft_dict: Dict[str, Any],
    ) -> str: ...
```

**Lazy Loading**: Services are loaded from `AppContainer` singleton on first access:

```python
@property
def resources_service(self) -> Any:
    if self._resources_service is None:
        container = self._get_app_container()
        if container:
            self._resources_service = container.resources_service
    return self._resources_service
```

---

## Exception Handling

Custom exception hierarchy for clear error reporting:

```python
BuilderError (base)
├── BuilderPhaseError      # Phase execution failure
│   └── Includes: phase name, cause exception
│
├── BuilderContextError    # Missing/invalid context
│   └── Default: "Builder context not available"
│
├── BuilderResourceError   # Missing required resources
│   └── Includes: resource_type
│
├── BuilderValidationError # Blueprint validation failure
│   └── Includes: validation_errors list
│
└── BuilderToolError       # Tool execution failure
    └── Includes: tool_name, cause exception
```

**Usage Example**:

```python
from .exceptions import BuilderResourceError

if not search_result.has_required_llm:
    raise BuilderResourceError(
        resource_type="llm",
        message="No LLM found. Cannot create workflow."
    )
```

---

## Frontend Integration

### SmartBuilderPanel.tsx

The React component that hosts the Smart Builder UI.

**Key Functions**:

```typescript
// Check if user has a Builder Agent
checkBuilderAgentExists(userId): Promise<BuilderAgentCheckResult>

// Create a session for the builder
createBuilderSession(userId, builderAgent): Promise<BuilderSession>

// Execute with streaming for real-time progress
executeBuilderRequestStreaming(
  sessionId: string,
  userPrompt: string,
  onPhaseEvent: (event: BuilderPhaseEvent) => void,
  onComplete: (response: BuilderExecuteResponse) => void,
  onError: (error: string) => void
): Promise<void>
```

**API Flow**:

```
1. Panel Opens
   └─> checkBuilderAgentExists(userId)
       └─> Check if builder_node exists in inventory
       
2. User Clicks Send
   └─> createBuilderSession(userId, builderAgent)
       ├─> Check for existing "Workflow Builder" blueprint
       ├─> Create new blueprint if needed (is_system: true)
       └─> Create session for execution
       
3. Execute with Streaming
   └─> executeBuilderRequestStreaming(sessionId, userPrompt, callbacks)
       ├─> POST /sessions/user.session.execute (stream: true)
       ├─> Parse NDJSON stream
       ├─> Call onPhaseEvent for each builder_phase event
       └─> Call onComplete with final response
```

**Response Format**:

```typescript
interface BuilderExecuteResponse {
  success: boolean;
  output: string;
  error?: string;
  metadata?: {
    phases_completed?: string[];
    blueprint_id?: string;
    workflow_name?: string;
    agents_created?: number;
    agents_reused?: number;
    uses_orchestrator?: boolean;
  };
}
```

---

## Streaming Events

The builder emits real-time events for frontend progress display.

### Event Structure

```python
# Emitted from BuilderNode._stream_phase_event()
{
    "type": "builder_phase",
    "phase": "analyze" | "search" | "design" | "validate",
    "status": "started" | "complete" | "failed",
    "message": "Understanding your request..."
}
```

### Streaming Flow

```
Backend                                    Frontend
───────                                    ────────
_run_builder_phases()
   │
   ├─> _stream_phase_event("analyze", "started", ...)
   │   └─> self._stream({...})  ─────────────────────> onPhaseEvent(event)
   │                                                        │
   ├─> _run_phase(ANALYZE)                                  ▼
   │                                                   Update UI: "Analyzing..."
   ├─> _stream_phase_event("analyze", "complete", ...)
   │   └─> self._stream({...})  ─────────────────────> onPhaseEvent(event)
   │                                                        │
   ...                                                      ▼
   │                                                   Update UI: ✓ Analyze
   ├─> Final result
       └─> AgentResult ──────────────────────────────> onComplete(response)
```

---

## Generated Blueprint Example

For request: "Create a workflow to search Jira and Confluence"

```json
{
  "name": "Jira & Confluence Workflow",
  "description": "Search Jira and Confluence for information",
  "providers": [],
  "llms": [],
  "retrievers": [],
  "tools": [],
  "conditions": [
    {
      "rid": "router_direct_rid",
      "name": "Router",
      "type": "router_direct",
      "config": { "type": "router_direct" }
    }
  ],
  "nodes": [
    {
      "rid": "user_question_node_rid",
      "name": "User Question Node",
      "type": "user_question_node",
      "config": { "type": "user_question_node" }
    },
    {
      "rid": "orchestrator_node_rid",
      "name": "Orchestrator",
      "type": "orchestrator_node",
      "config": {
        "type": "orchestrator_node",
        "llm": "$ref:llm_abc123",
        "system_message": "Orchestrate Jira and Confluence workflow..."
      }
    },
    {
      "rid": "existing_agent_0_rid",
      "name": "Jira Agent",
      "type": "custom_agent_node",
      "config": {
        "type": "custom_agent_node",
        "llm": "$ref:llm_abc123",
        "provider": "$ref:jira_mcp_xyz",
        "system_message": "You are an agent that uses Jira..."
      }
    },
    {
      "rid": "new_agent_1_rid",
      "name": "Confluence Agent",
      "type": "custom_agent_node",
      "config": {
        "type": "custom_agent_node",
        "llm": "$ref:llm_abc123",
        "provider": "$ref:confluence_mcp_def",
        "system_message": "You are an agent that uses Confluence..."
      }
    },
    {
      "rid": "final_answer_node_rid",
      "name": "Final Answer Node",
      "type": "final_answer_node",
      "config": { "type": "final_answer_node" }
    }
  ],
  "plan": [
    { "uid": "user_input", "node": "user_question_node_rid" },
    {
      "uid": "orchestrator",
      "after": ["user_input", "agent_0", "agent_1"],
      "node": "orchestrator_node_rid",
      "exit_condition": "router_direct_rid",
      "branches": {
        "agent_0": "agent_0",
        "agent_1": "agent_1",
        "finalize": "finalize"
      }
    },
    { "uid": "agent_0", "node": "existing_agent_0_rid" },
    { "uid": "agent_1", "node": "new_agent_1_rid" },
    { "uid": "finalize", "node": "final_answer_node_rid" }
  ]
}
```

---

## Usage

### Prerequisites

1. User must have at least one **LLM** resource in their inventory
2. User must have a **Builder Agent** (`builder_node`) in their inventory

### Example Requests

| Request | Result |
|---------|--------|
| "Create a Jira search workflow" | Single agent with Jira MCP |
| "Create a workflow for Jira and Confluence" | Orchestrated 2-agent workflow |
| "Create a sales agent" | LLM-only agent for sales tasks |
| "Search Jira, Confluence, and summarize with Slack" | 3-agent orchestrated workflow |

### Expected Flow

1. **ANALYZE**: Identifies capabilities and orchestration needs
2. **SEARCH**: Finds LLM, matching providers, existing agents
3. **DESIGN**: Creates/reuses agents, generates blueprint
4. **VALIDATE**: Validates, previews, saves to database

### Output

- New workflow blueprint saved to database
- New agents created in user's inventory (if needed)
- `blueprint_id` returned for immediate use

---

## Configuration

Settings in `config.py`:

```python
class BuilderNodeConfig:
    max_rounds: int = 20  # Max LLM iterations (divided by 4 per phase)
```

Configurable per-phase iteration limits via `BuilderPhaseProvider`:

| Phase | Default Max Iterations |
|-------|------------------------|
| ANALYZE | 5 |
| SEARCH | 3 |
| DESIGN | 5 |
| VALIDATE | 5 |
| COMPLETE | 1 |

---

## Error Handling Summary

| Scenario | Response |
|----------|----------|
| No LLM Found | Returns error asking user to add LLM first |
| Phase Failure | Returns error with phase name and details |
| Validation Errors | Blocks saving, returns error list |
| Validation Warnings | Logged, but saving proceeds |
| Service Unavailable | Falls back to inline configuration |
| Missing Context | Raises `BuilderContextError` |
| Missing Resources | Raises `BuilderResourceError` |

---

## External Dependencies & Changes

The Smart Builder feature requires changes outside the `builder/` folder. This section documents all external modifications.

### Backend Changes

#### 1. Blueprint Model (`blueprints/models/blueprint.py`)

Added `is_system` flag to hide internal blueprints from user listings:

```python
class BlueprintDraft(BaseModel):
    # ... existing fields ...
    is_system: bool = Field(
        default=False, 
        description="If True, this blueprint is a system/internal blueprint and should be hidden from regular listings"
    )
```

#### 2. Blueprint Repository (`blueprints/repository/repository.py`)

Added `include_system` parameter to listing methods:

```python
class BlueprintRepository(ABC):
    @abstractmethod
    def list_ids(self, user_id: str, include_system: bool = False) -> List[str]:
        """List blueprint IDs. By default excludes system blueprints."""
        ...
    
    @abstractmethod
    def list_docs(self, user_id: str, include_system: bool = False) -> List[BlueprintDraft]:
        """List blueprint documents. By default excludes system blueprints."""
        ...
```

#### 3. Blueprint Service (`blueprints/service.py`)

Updated listing methods to filter system blueprints:

```python
class BlueprintService:
    def list_ids(self, user_id: str, include_system: bool = False) -> List[str]:
        return self._repo.list_ids(user_id, include_system=include_system)
    
    def list_draft_dicts(self, user_id: str, include_system: bool = False) -> List[Dict]:
        docs = self._repo.list_docs(user_id, include_system=include_system)
        return [doc.model_dump() for doc in docs]
```

#### 4. Blueprint API Endpoints (`api/flask/endpoints/blueprints.py`)

Added `include_system` query parameter:

```python
@blueprints_bp.route("/available.blueprints.get", methods=["GET"])
def get_available_blueprints():
    user_id = request.args.get("userId", "")
    include_system = request.args.get("includeSystem", "false").lower() == "true"
    
    blueprints = blueprint_service.list_draft_dicts(user_id, include_system=include_system)
    return jsonify(blueprints)
```

#### 5. Session Execution Endpoint (`api/flask/endpoints/sessions.py`)

Supports streaming for real-time phase updates:

```python
@sessions_bp.route("/user.session.execute", methods=["POST"])
@from_body({
    "session_id": fields.Str(data_key="sessionId", required=True),
    "inputs": fields.Dict(data_key="inputs", required=True),
    "stream": fields.Bool(data_key="stream", load_default=False),
    "stream_mode": fields.List(fields.Str(), data_key="streamMode", load_default=lambda: ["custom"]),
})
def execute_user_session(session_id, inputs, stream, stream_mode):
    if not stream:
        # Synchronous execution
        result = svc.execute(session_id=session_id, inputs=inputs, ...)
        return json.dumps(result), 200
    
    # Streaming execution
    def generate():
        for chunk in svc.execute(
            session_id=session_id,
            inputs=inputs,
            stream=True,
            stream_mode=stream_mode,
        ):
            yield json.dumps(chunk) + "\n"
    
    return Response(generate(), mimetype="application/x-ndjson")
```

#### 6. Session Manager (`session/user_session_manager.py`)

Added method to check if a blueprint is a system blueprint:

```python
class UserSessionManager:
    def is_system_blueprint(self) -> bool:
        """Check if the current session's blueprint is a system blueprint."""
        if self._resolved_blueprint:
            return getattr(self._resolved_blueprint, 'is_system', False)
        return False
```

#### 7. Session Service (`session/service.py`)

Filters system blueprints from chat history:

```python
class SessionService:
    def get_user_sessions_chat_history(self, user_id: str, ...):
        sessions = self._get_user_sessions(user_id, ...)
        
        # Filter out sessions associated with system blueprints
        filtered = [
            s for s in sessions 
            if not self._is_system_session(s)
        ]
        return filtered
```

---

### Frontend Changes

#### 1. Smart Builder API (`ui/client/src/api/smartBuilder.ts`)

Complete API module for Smart Builder:

```typescript
// Check if builder agent exists in inventory
export async function checkBuilderAgentExists(userId: string): Promise<BuilderAgentCheckResult>

// Create session for builder workflow
export async function createBuilderSession(userId: string, builderAgent: any): Promise<BuilderSession>

// Execute with streaming for real-time progress
export async function executeBuilderRequestStreaming(
  sessionId: string,
  userPrompt: string,
  onPhaseEvent: (event: BuilderPhaseEvent) => void,
  onComplete: (response: BuilderExecuteResponse) => void,
  onError: (error: string) => void,
  onStreamEvent?: (event: BuilderStreamEvent) => void
): Promise<void>
```

**Key Implementation Details**:

```typescript
// Blueprint is marked as system to hide from regular listings
function buildBuilderBlueprintSpec(builderAgentRid: string, builderAgentConfig: any) {
  return {
    name: "Workflow Builder",
    description: "An intelligent agent that creates workflows...",
    is_system: true,  // Hidden from regular workflow listings
    nodes: [...],
    plan: [...],
  };
}

// Streaming parser handles LangGraph tuple format
// Each chunk arrives as: ["custom", {actual_data}]
const chunk = Array.isArray(parsed) && parsed.length === 2 
  ? parsed[1] 
  : parsed;
```

#### 2. Smart Builder Panel (`ui/client/src/components/agentic-ai/smart-builder/SmartBuilderPanel.tsx`)

Main UI component:

```typescript
interface SmartBuilderPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onWorkflowCreated?: (blueprintId: string) => void;
}

export default function SmartBuilderPanel({
  isOpen,
  onClose,
  onWorkflowCreated,
}: SmartBuilderPanelProps) {
  // State management
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [phaseStatuses, setPhaseStatuses] = useState<Record<string, PhaseStatus>>({...});
  
  // Handle streaming phase events
  const handlePhaseEvent = (event: BuilderPhaseEvent) => {
    setPhaseStatuses(prev => ({ ...prev, [event.phase]: event.status }));
    // Add log entry...
  };
  
  // Notify parent when workflow created
  const handleComplete = (response) => {
    if (response.success && onWorkflowCreated) {
      onWorkflowCreated("refresh");
    }
  };
}
```

#### 3. Agentic Workflows Page (`ui/client/src/pages/AgenticWorkflows.tsx`)

Integration with Smart Builder:

```typescript
export default function AgenticWorkflows() {
  const [showSmartBuilder, setShowSmartBuilder] = useState(false);
  const [workflowsRefreshTrigger, setWorkflowsRefreshTrigger] = useState(0);
  
  // Refresh workflow list when builder creates new workflow
  const handleWorkflowCreated = useCallback(() => {
    toast({ title: "Workflow Created", description: "Refreshing..." });
    setWorkflowsRefreshTrigger(prev => prev + 1);
  }, [toast]);
  
  return (
    <>
      <SmartBuilderPanel
        isOpen={showSmartBuilder}
        onClose={() => setShowSmartBuilder(false)}
        onWorkflowCreated={handleWorkflowCreated}
      />
      
      <AgentFlowGraph
        selectedFlow={selectedFlow}
        refreshTrigger={workflowsRefreshTrigger}
        ...
      />
    </>
  );
}
```

#### 4. Agent Flow Graph (`ui/client/src/components/agentic-ai/AgentFlowGraph.tsx`)

Passes refresh trigger to workflows panel:

```typescript
type AgentFlowGraphProps = {
  selectedFlow: FlowObject | null;
  refreshTrigger?: number;  // Added prop
  // ...
};

export default function AgentFlowGraph({
  refreshTrigger,
  ...
}: AgentFlowGraphProps) {
  return (
    <WorkflowsPanel
      refreshTrigger={refreshTrigger}
      ...
    />
  );
}
```

#### 5. Workflows Panel (`ui/client/src/components/agentic-ai/WorkflowsPanel.tsx`)

Re-fetches on refresh trigger:

```typescript
export interface WorkflowsPanelProps {
  refreshTrigger?: number;  // Added prop
  // ...
}

export default function WorkflowsPanel({
  refreshTrigger,
  ...
}: WorkflowsPanelProps) {
  // Re-fetch when refreshTrigger changes
  useEffect(() => {
    setIsLoading(true);
    Promise.all([
      fetchAvailableFlows(),
      fetchActiveFlows(),
    ]).finally(() => setIsLoading(false));
  }, [user, useResolvedEndpoint, refreshTrigger]);  // Added to deps
}
```

---

### File Summary

| Location | File | Change |
|----------|------|--------|
| **Backend** | `blueprints/models/blueprint.py` | Added `is_system` field |
| | `blueprints/repository/repository.py` | Added `include_system` param |
| | `blueprints/service.py` | Filter system blueprints |
| | `api/flask/endpoints/blueprints.py` | `includeSystem` query param |
| | `api/flask/endpoints/sessions.py` | Streaming support |
| | `session/user_session_manager.py` | `is_system_blueprint()` method |
| | `session/service.py` | Filter system sessions |
| **Frontend** | `api/smartBuilder.ts` | Complete Smart Builder API |
| | `smart-builder/SmartBuilderPanel.tsx` | Main UI component |
| | `pages/AgenticWorkflows.tsx` | Integration & refresh |
| | `AgentFlowGraph.tsx` | Pass refreshTrigger |
| | `WorkflowsPanel.tsx` | React to refreshTrigger |

# 🏗️ Builder Agent Node

A multi-phase AI agent that automatically creates workflow blueprints based on natural language user requests.

---

## Quick Start

**What is it?** An AI agent that converts natural language like *"Create a Jira and Confluence workflow"* into a complete, executable workflow blueprint.

**How does it work?**

```
User Request → ANALYZE → SEARCH → DESIGN → VALIDATE → Saved Workflow
                 │          │         │         │
                 ▼          ▼         ▼         ▼
             Extract    Find LLMs,  Build     Check &
           capabilities providers,  agents    save to
                       & agents    & plan      DB
```

**Key files to explore:**
- `builder_node.py` - Main orchestrator (start here)
- `tools/` - Phase-specific tools (one per phase)
- `context/builder_context.py` - State management
- `tools/helpers/` - Agent building and inventory logic

**Reading Guide:**

| If you want to... | Read... |
|-------------------|---------|
| Understand the big picture | [Overview](#overview) → [Architecture](#architecture) |
| Learn the 4-phase flow | [The 4 Phases](#the-4-phases) |
| Understand agent selection logic | [Workflow Creation Rules](#workflow-creation-rules) |
| See a generated blueprint | [Generated Blueprint Example](#generated-blueprint-example) |
| Integrate with frontend | [Frontend Integration](#frontend-integration) |
| Add a new agent inventory type | [Agent Inventory System Architecture](#agent-inventory-system-architecture) |
| Handle errors | [Exception Handling](#exception-handling) |

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [The 4 Phases](#the-4-phases)
4. [File Structure](#file-structure)
5. [Core Classes](#core-classes)
6. [Tools](#tools)
7. [Agent Inventory System Architecture](#agent-inventory-system-architecture)
8. [Helper Classes](#helper-classes)
9. [Data Models](#data-models)
10. [Prompts System](#prompts-system)
11. [Service Protocols](#service-protocols)
12. [Exception Handling](#exception-handling)
13. [Frontend Integration](#frontend-integration)
14. [Streaming Events](#streaming-events)
15. [Generated Blueprint Example](#generated-blueprint-example)
16. [Usage](#usage)
17. [Workflow Creation Rules](#workflow-creation-rules)
18. [Configuration](#configuration)
19. [Error Handling Summary](#error-handling-summary)
20. [External Dependencies & Changes](#external-dependencies--changes)

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
- **Smart Agent Reuse**: Reuses existing agents when appropriate (Custom preferred over A2A)
- **Single Agent Selection**: Only ONE agent per capability type is selected
- **Agent Inventory System**: Unified discovery across multiple agent sources
- **Skill-Based Matching**: Intelligent matching using agent card metadata, skills, and tags
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
| Custom Agents | Reusable `custom_agent_node` agents | Optional |
| A2A Agents | Remote agents via `a2a_agent_node` | Optional |
| Orchestrators | Existing orchestrator nodes | Optional |

**Agent Inventory System**:
The search phase uses the `InventoryRegistry` to discover agents across multiple sources:

```python
# Search specific inventories
agent_inventories: ["custom_agents", "a2a_agents"]

# InventoryRegistry searches all registered inventories
results = inventory_registry.search(
    resources_service=resources_service,
    user_id=user_id,
    capability_filter=["jira", "charting"],
    provider_list=matched_providers,
)
```

**Matching Logic**:
- Provider matching is **STRICT**: Only matches if capability appears in provider name
- Custom Agent matching: 
  - Builds `provider_rid → [capabilities]` mapping from matched providers
  - Agent only gets capabilities that **its specific provider** handles
  - Prevents one agent from claiming all requested capabilities
- A2A Agent matching: Uses `SkillMatcher` to analyze the `agent_card` metadata:
  - Agent name
  - Agent card name and description
  - Skill names and descriptions
  - Tags
- Prevents false positives (e.g., Jira agent won't match "sales" capability)

**Output**: `ResourceSearchResult` stored in `BuilderContext.state.search_result`

```python
class ResourceSearchResult(BaseModel):
    llms: List[Dict[str, Any]] = []                  # Available LLMs
    providers: List[Dict[str, Any]] = []             # Matched providers
    existing_nodes: List[Dict[str, Any]] = []        # Reusable custom agents
    existing_a2a_agents: List[Dict[str, Any]] = []   # Reusable A2A agents
    existing_orchestrators: List[Dict[str, Any]] = []
    missing_capabilities: List[str] = []             # Capabilities not found
    has_required_llm: bool = False                   # MUST be True to proceed
    
    @property
    def all_reusable_agents(self) -> List[Dict[str, Any]]:
        """Get all reusable agents (custom + A2A) as a unified list."""
        
    @property
    def total_agent_count(self) -> int:
        """Get total count of all reusable agents."""
```

---

### Phase 3: DESIGN

**Purpose**: Generate the complete workflow blueprint.

**Tool**: `GenerateBlueprintTool`

**Key Components**:

1. **AgentBuilder Helper**: Creates agent nodes with priority:
   - First: Reuse BEST existing custom agent matching capabilities (preferred)
   - Second: Reuse BEST existing A2A agent for uncovered capabilities (via `SkillMatcher`)
   - Third: Create new agents for matched providers
   - Fourth: Create LLM-only agents for remaining capabilities
   
   **Note**: Only ONE agent per capability type is selected. Custom agents are preferred over A2A agents.

2. **PlanBuilder Helper**: Creates execution plan:
   - Single agent: `user_question → agent → final_answer`
   - Orchestrated: `user_question → orchestrator → [agents] → final_answer`

**What gets generated**:
- `user_question_node` (entry point)
- `orchestrator_node` (if needed)
- Agent nodes (`custom_agent_node` or `a2a_agent_node`)
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
├── builder_node.py             # Main BuilderNode class
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
        ├── agent_builder.py      # AgentBuilder class
        ├── plan_builder.py       # PlanBuilder class
        ├── agent_inventory.py    # InventoryType, SkillMatcher, AgentInfo, AgentInventory (ABCs & impls)
        └── inventory_registry.py # InventoryRegistry singleton
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

Searches for available resources in the user's inventory using the Agent Inventory System.

```python
class SearchResourcesArgs(BaseModel):
    agent_inventories: Optional[List[str]] = None  # ["custom_agents", "a2a_agents"]
    # If None, searches all registered inventories

class SearchResourcesTool(BaseTool):
    name = "search_resources"
    
    def run(self, **kwargs) -> Dict[str, Any]:
        context = self._get_context()
        resources_service = context.resources_service
        user_id = context.user_id
        args = SearchResourcesArgs(**kwargs)
        
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
        
        # Search for agents using InventoryRegistry
        inventory_types = inventory_registry.parse_inventory_types(
            args.agent_inventories
        )
        agent_results = inventory_registry.search(
            resources_service=resources_service,
            user_id=user_id,
            inventories=inventory_types,
            capability_filter=required_capabilities,
            provider_list=provider_list,
        )
        
        # Split results by type
        custom_agents = [
            a.to_dict() 
            for a in agent_results.get(InventoryType.CUSTOM_AGENTS, [])
        ]
        a2a_agents = [
            a.to_dict() 
            for a in agent_results.get(InventoryType.A2A_AGENTS, [])
        ]
        
        # Create ResourceSearchResult
        result = ResourceSearchResult(
            llms=llm_list,
            providers=provider_list,
            existing_nodes=custom_agents,
            existing_a2a_agents=a2a_agents,
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
        
        # Use AgentBuilder helper FIRST to know actual agent count
        agent_builder = AgentBuilder(
            llm_rid=llm_rid,
            resources_service=context.resources_service,
            user_id=context.user_id
        )
        agent_result = agent_builder.build_agents(
            existing_agents=search_result.existing_nodes,        # Custom agents
            existing_a2a_agents=search_result.existing_a2a_agents,  # A2A agents
            matched_providers=search_result.providers,
            required_capabilities=required_caps
        )
        
        # Determine if orchestrator needed AFTER we know final agent count
        # This prevents adding orchestrator when only 1 agent will be used
        final_agent_count = len(agent_result.agent_nodes)
        needs_orchestrator = (
            (analysis and analysis.needs_orchestrator) or 
            final_agent_count > 1  # Based on ACTUAL agents, not search results
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
        
        # Add agent nodes (custom_agent_node or a2a_agent_node)
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

Validates the generated blueprint before saving.

**Uses Shared Validation Infrastructure**: The builder reuses the same validation system used when users create workflows manually via the UI. The `BlueprintService.validate_draft()` method is the shared entry point for both:

| Trigger | Entry Point | Validation Path |
|---------|-------------|-----------------|
| Manual workflow creation | `/draft.validate` API | `BlueprintService.validate_draft()` → `ElementValidationService` |
| Builder workflow creation | `ValidateBlueprintTool` | Builder checks → `BlueprintService.validate_draft()` → `ElementValidationService` |

The builder adds **additional structural checks** before delegating to the shared validation service.

```python
class ValidateBlueprintArgs(BaseModel):
    timeout_seconds: float = Field(default=10.0, description="Timeout for validation checks")


class ValidateBlueprintTool(BaseTool):
    name = "validate_blueprint"
    description = """Validate the generated workflow blueprint.

Checks:
- Schema validation (all required fields present)
- Resource references are valid
- Element-specific validation (LLM connectivity, provider health, etc.)

Returns validation results with any errors or warnings.
If validation fails, you may need to fix issues and try again."""
    
    args_schema = ValidateBlueprintArgs
    
    def run(self, **kwargs) -> Dict[str, Any]:
        args = ValidateBlueprintArgs(**kwargs)
        context = self._get_context()
        blueprint = context.state.design_result.blueprint_draft
        
        errors = []
        warnings = []
        suggestions = []
        
        # ====== VALIDATION 1: Basic Structure ======
        if not blueprint.get("name"):
            errors.append({"field": "name", "message": "Workflow name is required"})
        
        if not blueprint.get("plan"):
            errors.append({"field": "plan", "message": "Workflow plan is required"})
        
        # ====== VALIDATION 2: Required Nodes ======
        nodes = blueprint.get("nodes", [])
        node_rids = {n.get("rid") for n in nodes}
        
        has_user_question = any(n.get("type") == "user_question_node" for n in nodes)
        has_final_answer = any(n.get("type") == "final_answer_node" for n in nodes)
        
        if not has_user_question:
            errors.append({
                "field": "nodes",
                "message": "Workflow must include a user_question_node"
            })
        if not has_final_answer:
            errors.append({
                "field": "nodes",
                "message": "Workflow must include a final_answer_node"
            })
        
        # ====== VALIDATION 3: Plan References Valid Nodes ======
        plan = blueprint.get("plan", [])
        for step in plan:
            node_ref = step.get("node")
            if node_ref:
                # $ref: references point to external resources (resolved at runtime)
                if node_ref.startswith("$ref:"):
                    continue  # External reference - will be resolved from resource registry
                elif node_ref not in node_rids:
                    errors.append({
                        "field": f"plan.{step.get('uid')}",
                        "message": f"Step references unknown node: {node_ref}"
                    })
        
        # ====== VALIDATION 4: LLM References in Agent Nodes ======
        for node in nodes:
            if node.get("type") in ["custom_agent_node", "orchestrator_node"]:
                config = node.get("config", {})
                if not config.get("llm"):
                    warnings.append({
                        "field": f"nodes.{node.get('rid')}",
                        "message": f"Agent node '{node.get('name')}' has no LLM configured"
                    })
        
        # ====== VALIDATION 5: Blueprint Service Validation ======
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
                                    errors.append({"field": rid, "message": msg.message})
                                elif msg.severity.value == "warning":
                                    warnings.append({"field": rid, "message": msg.message})
            except Exception as e:
                warnings.append({
                    "field": "validation",
                    "message": f"Full validation unavailable: {str(e)}"
                })
        
        # ====== SUGGESTIONS ======
        if warnings:
            suggestions.append("Consider addressing the warnings for a more robust workflow")
        if len(nodes) > 5:
            suggestions.append("Large workflow detected. Consider breaking into smaller sub-workflows")
        
        is_valid = len(errors) == 0
        
        # Update context state
        context.state.validation_result = ValidationResult(
            is_valid=is_valid,
            validation_errors=errors,
            validation_warnings=warnings,
            suggestions=suggestions,
        )
        
        return {
            "success": True,
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "message": "Validation passed" if is_valid else f"Validation failed with {len(errors)} error(s)"
        }
```

**Validation Summary Table:**

| # | Validation | Type | Blocking? |
|---|-----------|------|-----------|
| 1 | Workflow name present | Basic | ✅ Yes (error) |
| 2 | Workflow plan present | Basic | ✅ Yes (error) |
| 3 | `user_question_node` exists | Structure | ✅ Yes (error) |
| 4 | `final_answer_node` exists | Structure | ✅ Yes (error) |
| 5 | Plan steps reference valid nodes | References | ✅ Yes (error) |
| 6 | Agent nodes have LLM configured | Config | ⚠️ No (warning) |
| 7 | Blueprint service deep validation | Service | Mixed |

**Reference Handling:**
- `$ref:` prefixes indicate external resources (LLMs, providers) resolved at runtime
- Only inline node references are validated against `node_rids`

---

### Shared Validation Architecture

The builder integrates with the platform's existing validation infrastructure, ensuring consistent validation whether workflows are created manually or via the builder.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VALIDATION ARCHITECTURE                                   │
│                                                                              │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────────┐ │
│  │   MANUAL WORKFLOW CREATION   │    │   BUILDER WORKFLOW CREATION         │ │
│  │                              │    │                                     │ │
│  │   UI → /draft.validate API   │    │   BuilderNode → ValidateBlueprintTool│ │
│  │             │                │    │             │                       │ │
│  │             ▼                │    │   ┌─────────┴──────────┐            │ │
│  │                              │    │   │ Builder-specific    │            │ │
│  │                              │    │   │ validations:        │            │ │
│  │                              │    │   │ • name required     │            │ │
│  │                              │    │   │ • plan required     │            │ │
│  │                              │    │   │ • required nodes    │            │ │
│  │                              │    │   │ • plan references   │            │ │
│  │                              │    │   │ • LLM warnings      │            │ │
│  │                              │    │   └─────────┬──────────┘            │ │
│  │                              │    │             │                       │ │
│  │                              │    │             ▼                       │ │
│  └─────────────┬────────────────┘    └─────────────┬───────────────────────┘ │
│                │                                   │                         │
│                └───────────────┬───────────────────┘                         │
│                                ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │              SHARED: BlueprintService.validate_draft()                   │ │
│  │                                                                          │ │
│  │   1. resolve_draft_dict() - Resolve $ref: references                     │ │
│  │   2. _config_collector.collect() - Collect configs from spec             │ │
│  │   3. _validation_service.validate_ordered() - Validate each element      │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                │                                             │
│                                ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │              SHARED: ElementValidationService                            │ │
│  │                                                                          │ │
│  │   For each element in blueprint:                                         │ │
│  │   1. Look up validator from ElementRegistry                              │ │
│  │   2. Call validator.validate(config, context)                            │ │
│  │   3. Collect messages (errors, warnings, info)                           │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                │                                             │
│                                ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │              ELEMENT-SPECIFIC VALIDATORS                                 │ │
│  │                                                                          │ │
│  │   elements/llms/openai/validator.py          → OpenAILLMValidator        │ │
│  │   elements/llms/google_genai/validator.py    → GoogleGenAIValidator      │ │
│  │   elements/nodes/custom_agent/validator.py   → CustomAgentValidator      │ │
│  │   elements/nodes/a2a_agent/validator.py      → A2AAgentValidator         │ │
│  │   elements/nodes/orchestrator/validator.py   → OrchestratorValidator     │ │
│  │   elements/providers/mcp_server_client/...   → MCPServerValidator        │ │
│  │   ... (each element type has its own validator)                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Classes:**

| Class | Location | Purpose |
|-------|----------|---------|
| `BlueprintService` | `blueprints/service.py` | Orchestrates blueprint validation |
| `ElementValidationService` | `validation/service.py` | Validates individual elements |
| `ElementValidator` (ABC) | `elements/common/validator.py` | Interface for element validators |
| `BaseElementValidator` | `elements/common/validator.py` | Base class with utilities |
| `ValidationContext` | `elements/common/validator.py` | Context passed to validators |
| `BlueprintValidationResult` | `validation/models.py` | Blueprint-level result |
| `ElementValidationResult` | `elements/common/validator.py` | Element-level result |

**Element Validators Check:**

| Element Type | Validator Checks |
|-------------|------------------|
| LLMs (OpenAI, Google) | API key validity, endpoint reachability |
| Custom Agent | LLM dependency valid, provider dependency valid |
| A2A Agent | Base URL reachable, agent card accessible |
| MCP Server | Server process health, tool availability |
| Orchestrator | LLM dependency valid |

**Why Two Layers?**

1. **Builder Layer (Validations 1-6)**: Catches structural issues specific to builder-generated blueprints before expensive service calls
2. **Service Layer (Validation 7)**: Runs element-specific validators that may involve network calls (LLM connectivity, MCP health)

This ensures the builder fails fast on obvious issues while still benefiting from the full validation system.

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

## Agent Inventory System Architecture

This section explains the Agent Inventory System from high-level concepts down to implementation details.

### Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT INVENTORY SYSTEM                               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     HIGH LEVEL: Entry Points                         │    │
│  │                                                                      │    │
│  │    SearchResourcesTool ──────────► InventoryRegistry (Singleton)     │    │
│  │          │                               │                           │    │
│  │          │ Uses                          │ Searches                  │    │
│  │          ▼                               ▼                           │    │
│  │    AgentBuilder ◄────────────────── AgentInfo[]                      │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     MID LEVEL: Abstractions                          │    │
│  │                                                                      │    │
│  │    InventoryRegistry                                                 │    │
│  │         │                                                            │    │
│  │         ├── register(AgentInventory)                                 │    │
│  │         ├── search() → Dict[InventoryType, List[AgentInfo]]          │    │
│  │         └── search_all() → List[AgentInfo]                           │    │
│  │                │                                                     │    │
│  │                ▼                                                     │    │
│  │    AgentInventory (ABC)  ◄─── ResourcesServiceProtocol               │    │
│  │         │                      (from protocols.py)                   │    │
│  │         └── search() → List[AgentInfo]                               │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     LOW LEVEL: Implementations                       │    │
│  │                                                                      │    │
│  │    CustomAgentInventory              A2AAgentInventory               │    │
│  │         │                                  │                         │    │
│  │         ├── Searches "nodes"               ├── Searches "nodes"      │    │
│  │         │   category for                   │   category for          │    │
│  │         │   "custom_agent_node"            │   "a2a_agent_node"      │    │
│  │         │                                  │                         │    │
│  │         └── Matches by:                    └── Matches by:           │    │
│  │             • Agent name                       • SkillMatcher        │    │
│  │             • Provider name                    • Agent card skills   │    │
│  │                                                • Agent card tags     │    │
│  │                                                • Descriptions        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     UTILITIES: Shared Components                     │    │
│  │                                                                      │    │
│  │    SkillMatcher                      AgentInfo (Pydantic DTO)        │    │
│  │         │                                  │                         │    │
│  │         ├── matches(cap, text)             ├── rid, name, node_type  │    │
│  │         ├── match_any(caps, text)          ├── source_type (enum)    │    │
│  │         ├── _split_compound()              ├── Custom fields (llm,   │    │
│  │         └── _get_roots()                   │   provider, etc.)       │    │
│  │                                            ├── A2A fields (base_url, │    │
│  │    InventoryType (Enum)                    │   skills, tags, etc.)   │    │
│  │         ├── CUSTOM_AGENTS                  ├── is_a2a() / is_custom()│    │
│  │         └── A2A_AGENTS                     ├── to_dict()             │    │
│  │                                            └── to_blueprint_node()   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Class Hierarchy (High → Low)

#### Level 1: Entry Points (Consumer Layer)

| Class | Purpose | Location |
|-------|---------|----------|
| `SearchResourcesTool` | Phase 2 tool that triggers agent discovery | `tools/search_resources.py` |
| `AgentBuilder` | Uses discovered agents to build blueprint nodes | `tools/helpers/agent_builder.py` |

These are the **consumers** of the inventory system. They don't know implementation details.

#### Level 2: Registry (Orchestration Layer)

| Class | Purpose | Pattern |
|-------|---------|---------|
| `InventoryRegistry` | Singleton that manages all inventory implementations | Registry + Singleton |

**Key Responsibilities:**
- Registers inventory implementations at startup
- Routes search requests to appropriate inventories
- Aggregates results from multiple sources
- Thread-safe with `RLock`

```python
# How it works
inventory_registry = InventoryRegistry()  # Singleton
inventory_registry.register(CustomAgentInventory())
inventory_registry.register(A2AAgentInventory())

# Search routes to both implementations
results = inventory_registry.search(resources_service, user_id)
# Returns: {CUSTOM_AGENTS: [...], A2A_AGENTS: [...]}
```

#### Level 3: Abstract Base (Contract Layer)

| Class | Purpose | Pattern |
|-------|---------|---------|
| `AgentInventory` | ABC defining the contract for all inventories | Strategy + Template |
| `ResourcesServiceProtocol` | Protocol for dependency injection | Protocol (structural typing) |

**Key Contract:**
```python
class AgentInventory(ABC):
    @property
    @abstractmethod
    def inventory_type(self) -> InventoryType: ...
    
    @abstractmethod
    def search(...) -> List[AgentInfo]: ...
```

#### Level 4: Implementations (Concrete Layer)

| Class | Inventory Type | Matching Logic |
|-------|----------------|----------------|
| `CustomAgentInventory` | `CUSTOM_AGENTS` | Name + Provider matching |
| `A2AAgentInventory` | `A2A_AGENTS` | Skill-based matching via `SkillMatcher` |

**CustomAgentInventory:**
- Searches for `custom_agent_node` resources
- Uses `_build_provider_caps_map()` to create `provider_rid → [capabilities]` mapping
- Agent only gets capabilities that **its specific provider** matches (not all requested)
- Prevents false positives (e.g., Jira agent won't claim "sales" capability)

**A2AAgentInventory:**
- Searches for `a2a_agent_node` resources  
- Extracts metadata from `agent_card` (skills, descriptions, tags)
- Uses `SkillMatcher` for flexible text matching

#### Level 5: Utilities (Foundation Layer)

| Class | Purpose |
|-------|---------|
| `SkillMatcher` | Text matching utility for capability-to-skill matching |
| `AgentInfo` | Unified DTO representing agents from any source |
| `InventoryType` | Enum identifying inventory sources |

### Data Flow Example

```
User Request: "Create a workflow for charting and Jira"
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Phase 1: ANALYZE                                             │
│  └─► required_capabilities = ["charting", "jira"]             │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Phase 2: SEARCH (SearchResourcesTool)                        │
│                                                               │
│  1. inventory_registry.search(                                │
│        capability_filter=["charting", "jira"]                 │
│     )                                                         │
│                                                               │
│  2. CustomAgentInventory.search()                             │
│     └─► _build_provider_caps_map: {"jira_mcp": ["jira"]}      │
│     └─► Finds "Jira Agent" with matched_capabilities: ["jira"]│
│         (NOT ["charting", "jira"] - only its provider's caps) │
│                                                               │
│  3. A2AAgentInventory.search()                                │
│     └─► Finds "Analytics Agent"                               │
│         └─► SkillMatcher.matches("charting", "create_chart")  │
│             └─► "chart" found in "create_chart" ✓             │
│                                                               │
│  Result:                                                      │
│  ├── existing_nodes: [JiraAgent(caps=["jira"])]               │
│  └── existing_a2a_agents: [AnalyticsAgent(caps=["charting"])] │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Phase 3: DESIGN (AgentBuilder + GenerateBlueprintTool)       │
│                                                               │
│  1. Build agents with priority order:                         │
│     Step 1: Select BEST custom agent (preferred)              │
│     └─► Custom: JiraAgent selected (matched "jira")           │
│     └─► used_capabilities = {"jira"}                          │
│                                                               │
│     Step 2: Select BEST A2A agent for UNCOVERED capabilities  │
│     └─► uncovered = {"charting"} (jira already covered)       │
│     └─► A2A: AnalyticsAgent selected (matched "charting")     │
│     └─► used_capabilities = {"jira", "charting"}              │
│                                                               │
│     └─► final_agent_count = 2                                 │
│                                                               │
│  2. Determine orchestrator AFTER building:                    │
│     └─► final_agent_count > 1 → needs_orchestrator = True     │
│                                                               │
│  Result: 2 agents reused, 0 created, orchestrator added       │
└──────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

| Principle | Implementation |
|-----------|----------------|
| **Open/Closed** | Add new inventory types without modifying existing code |
| **Single Responsibility** | Each class has one clear purpose |
| **Dependency Inversion** | High-level modules depend on abstractions (ABC, Protocol) |
| **DRY** | `AgentInfo` is the single DTO for all agent types |
| **Testability** | Easy to mock `ResourcesServiceProtocol` and `AgentInventory` |

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Custom agents preferred over A2A** | Custom agents are user-configured and run locally, preferred for same capability |
| **Only ONE agent per capability** | Prevents duplicate capability coverage and simplifies workflows |
| **Provider → Capabilities mapping** | Custom agents only get capabilities their specific provider matches, preventing false positives when searching for multiple capabilities |
| **Orchestrator decision AFTER build** | Determine `needs_orchestrator` based on `final_agent_count` (actual agents in workflow), not total search results |
| **Build agents before orchestrator** | Ensures single-agent workflows don't get unnecessary orchestrators |

### Quick Reference: File → Classes

```
protocols.py
└── ResourcesServiceProtocol      # Shared protocol (single source)

tools/helpers/agent_inventory.py
├── InventoryType                 # Enum: CUSTOM_AGENTS, A2A_AGENTS
├── SkillMatcher                  # Text matching utility
├── AgentInfo                     # Unified DTO (Pydantic)
├── AgentInventory                # ABC
├── CustomAgentInventory          # Implementation
└── A2AAgentInventory             # Implementation

tools/helpers/inventory_registry.py
├── InventoryRegistry             # Singleton registry
├── get_inventory_registry()      # Factory function
└── inventory_registry            # Module-level instance
```

---

## Helper Classes

### AgentBuilder

Handles agent node creation with smart reuse logic for both Custom and A2A agents.

**Key Behavior**: Only ONE agent per capability type is selected. Custom agents are preferred over A2A agents.

```python
@dataclass
class AgentBuildResult:
    agent_nodes: List[Dict[str, Any]] = field(default_factory=list)
    created_agent_rids: List[str] = field(default_factory=list)
    used_capabilities: Set[str] = field(default_factory=set)
    agents_created: int = 0
    agents_reused: int = 0
    custom_agents_reused: int = 0
    a2a_agents_reused: int = 0

class AgentBuilder:
    """Builds agent nodes for workflow blueprints."""
    
    def __init__(self, llm_rid: str, resources_service: Any, user_id: str):
        self.llm_rid = llm_rid
        self.resources_service = resources_service
        self.user_id = user_id
    
    def build_agents(
        self,
        existing_agents: List[Dict],           # Custom agents
        existing_a2a_agents: List[Dict],       # A2A agents
        matched_providers: List[Dict],
        required_capabilities: Set[str]
    ) -> AgentBuildResult:
        """Build agent nodes with priority order. Only ONE agent per capability."""
        result = AgentBuildResult()
        
        # Step 1: Select BEST custom agent matching capabilities (preferred)
        matching_custom = self._select_best_agent(existing_agents, required_capabilities, result.used_capabilities)
        if matching_custom:
            self._add_existing_agent(matching_custom, result)
        
        # Step 2: Select BEST A2A agent for uncovered capabilities
        matching_a2a = self._select_best_a2a_agent(existing_a2a_agents, required_capabilities, result.used_capabilities)
        if matching_a2a:
            self._add_a2a_agent(matching_a2a, result)
        
        # Step 3: Create agents for matched providers
        self._create_provider_agents(matched_providers, required_capabilities, result)
        
        # Step 4: Create LLM-only agents for remaining capabilities
        self._create_llm_only_agents(required_capabilities, result)
        
        return result
    
    def _select_best_agent(self, agents, required_capabilities, used_capabilities) -> Optional[Dict]:
        """Select the BEST single custom agent that covers the most uncovered capabilities."""
        # See detailed algorithm below
        
    def _select_best_a2a_agent(self, a2a_agents, required_capabilities, used_capabilities) -> Optional[Dict]:
        """Select the BEST single A2A agent for uncovered capabilities."""
        # See detailed algorithm below
        
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

**Priority Order** (Only ONE agent selected per step):
1. **Reuse BEST custom agent** matching capabilities (preferred over A2A)
2. **Reuse BEST A2A agent** for uncovered capabilities (skill-based matching via `SkillMatcher`)
3. **Create new agents** for providers matching capabilities (saved to inventory)
4. **Create LLM-only agents** for remaining capabilities (no provider)

**Agent Selection Behavior**:

| Scenario | Behavior |
|----------|----------|
| 2 custom agents matching same capability | 1 is added (best match by capability count) |
| 2 A2A agents matching same capability | 1 is added (best match by capability count) |
| 1 A2A + 1 Custom (same capability) | **Custom is added** (A2A skipped - custom preferred) |

#### Algorithm: `_select_best_agent()` (Custom Agents)

Selects the single best custom agent by counting how many **relevant uncovered capabilities** each agent matches.

```python
def _select_best_agent(self, agents, required_capabilities, used_capabilities) -> Optional[Dict]:
    if not agents:
        return None
    
    required_lower = {cap.lower() for cap in required_capabilities}
    best_agent = None
    best_match_count = 0
    
    for agent in agents:
        # Get this agent's matched capabilities
        agent_caps = set(cap.lower() for cap in agent.get("matched_capabilities", []))
        
        # Only consider capabilities NOT already covered
        uncovered_caps = agent_caps - used_capabilities
        
        # Only count capabilities that are actually required
        relevant_caps = uncovered_caps & required_lower
        
        # Select agent with the MOST relevant uncovered capabilities
        if len(relevant_caps) > best_match_count:
            best_match_count = len(relevant_caps)
            best_agent = agent
    
    return best_agent
```

**Algorithm Steps:**
1. Convert all capabilities to lowercase for comparison
2. For each agent, get its `matched_capabilities`
3. Remove capabilities already covered (`used_capabilities`)
4. Intersect with required capabilities to get relevant matches
5. Select the agent with the **highest count** of relevant uncovered capabilities
6. Return `None` if no agent has any relevant uncovered capabilities

**Example:**

```
required_capabilities = {"jira", "confluence", "slack"}
used_capabilities = {}  # Empty initially

Agent A: matched_capabilities = ["jira"]
Agent B: matched_capabilities = ["jira", "confluence"]
Agent C: matched_capabilities = ["slack"]

Calculation:
- Agent A: uncovered = {"jira"} ∩ required = {"jira"} → count = 1
- Agent B: uncovered = {"jira", "confluence"} ∩ required = {"jira", "confluence"} → count = 2
- Agent C: uncovered = {"slack"} ∩ required = {"slack"} → count = 1

Result: Agent B selected (highest count = 2)
```

#### Algorithm: `_select_best_a2a_agent()` (A2A Agents)

Similar to custom agent selection, but only considers **uncovered capabilities** (capabilities not already handled by custom agents).

```python
def _select_best_a2a_agent(self, a2a_agents, required_capabilities, used_capabilities) -> Optional[Dict]:
    if not a2a_agents:
        return None
    
    # Calculate what's still uncovered
    required_lower = {cap.lower() for cap in required_capabilities}
    uncovered = required_lower - used_capabilities
    
    if not uncovered:
        return None  # All capabilities already covered!
    
    # Match A2A agents against ONLY uncovered capabilities
    matching = self._match_a2a_by_skills(a2a_agents, uncovered)
    if not matching:
        return None
    
    # Return first matching agent (already sorted by match count in inventory search)
    return matching[0]
```

**Key Difference from Custom Agent Selection:**
- A2A selection uses `SkillMatcher` for flexible text matching (handles compound words, suffixes, etc.)
- Only searches for **uncovered** capabilities (those not already covered by custom agent)
- Returns the first match from already-sorted list

**Example:**

```
required_capabilities = {"jira", "charting"}
used_capabilities = {"jira"}  # Jira already covered by custom agent

uncovered = {"charting"}  # Only charting needs coverage

A2A Agent "Analytics Agent":
  - agent_card_skills = ["create_chart", "analyze_data"]
  - SkillMatcher.matches("charting", "create_chart") → True (found "chart")

Result: Analytics Agent selected for "charting"
```

---

### SkillMatcher

Utility for matching required capabilities to agent skills using flexible text matching.

```python
class SkillMatcher:
    """
    Utility for matching required capabilities to agent skills.
    
    Uses flexible text matching that handles:
    - Substring matching (e.g., "chart" in "create_chart")
    - Compound words (e.g., "chart_generator" → check "chart" and "generator")
    - Common word forms (e.g., "charting" → "chart")
    """
    
    # Common suffixes to strip for root matching
    SUFFIXES = ("ing", "tion", "ment", "ics", "er", "or", "s", "ed", "ly")
    
    # Separators for compound words
    SEPARATORS = ("_", "-", " ", ".")
    
    @classmethod
    def matches(cls, capability: str, searchable_text: str) -> bool:
        """
        Check if a capability matches within searchable text.
        
        Matching strategies (in order):
        1. Direct substring match
        2. Split compound words and check each part
        3. Root word match (remove suffixes from each part)
        """
        
    @classmethod
    def match_any(cls, capabilities: Set[str], searchable_text: str) -> List[str]:
        """Find all capabilities that match in searchable text."""
```

**Examples**:

| Capability | Split Parts | Matches Agent With |
|------------|-------------|-------------------|
| `chart_generator` | `["chart", "generator"]` | skill: `"create_chart"` ✅ |
| `jira_integration` | `["jira", "integration"]` | name: `"Jira Agent"` ✅ |
| `data_analysis` | `["data", "analysis"]` | skill: `"analyze_data"` ✅ |
| `reporting` | root: `"report"` | description: `"generates reports"` ✅ |

---

### AgentInventory

Abstract base class for agent inventory implementations.

**Note**: `ResourcesServiceProtocol` is imported from `protocols.py` to avoid duplication.

```python
from elements.nodes.builder.protocols import ResourcesServiceProtocol

class InventoryType(str, Enum):
    """Available agent inventory types."""
    CUSTOM_AGENTS = "custom_agents"
    A2A_AGENTS = "a2a_agents"


class AgentInfo(BaseModel):
    """Unified agent information from any inventory."""
    rid: str
    name: str
    source_type: InventoryType
    node_type: str
    matched_capabilities: List[str] = []
    description: str = ""
    
    # Custom agent fields
    system_message: Optional[str] = None
    llm: Optional[str] = None
    provider: Optional[str] = None
    
    # A2A agent fields
    base_url: Optional[str] = None
    bearer_token: Optional[str] = None
    agent_card_name: Optional[str] = None
    agent_card_description: Optional[str] = None
    agent_card_skills: List[str] = []
    agent_card_skill_descriptions: List[str] = []
    agent_card_tags: List[str] = []
    
    def is_a2a(self) -> bool: ...
    def is_custom(self) -> bool: ...
    def to_dict(self) -> Dict[str, Any]: ...
    def to_blueprint_node(self) -> Dict[str, Any]: ...


class AgentInventory(ABC):
    """Abstract base for agent inventories."""
    
    @property
    @abstractmethod
    def inventory_type(self) -> InventoryType: ...
    
    @abstractmethod
    def search(
        self,
        resources_service: ResourcesServiceProtocol,
        user_id: str,
        capability_filter: Optional[List[str]] = None,
        provider_list: Optional[List[Dict[str, Any]]] = None,
        limit: int = 50,
    ) -> List[AgentInfo]: ...
```

**Implementations**:
- `CustomAgentInventory`: Discovers `custom_agent_node` resources
  - Uses `_build_provider_caps_map(provider_list)` to map provider RIDs to their matched capabilities
  - Ensures agents only get capabilities their specific provider actually matches
- `A2AAgentInventory`: Discovers `a2a_agent_node` resources with skill matching

---

### InventoryRegistry

Singleton registry for agent inventory implementations.

```python
class InventoryRegistry(metaclass=SingletonMeta):
    """
    Registry for agent inventory implementations.
    
    Uses Singleton pattern for global access.
    Thread-safe with RLock for concurrent access.
    """
    
    def register(self, inventory: AgentInventory) -> None:
        """Register an inventory implementation."""
        
    def search(
        self,
        resources_service: ResourcesServiceProtocol,
        user_id: str,
        inventories: Optional[List[InventoryType]] = None,
        capability_filter: Optional[List[str]] = None,
        provider_list: Optional[List[Dict[str, Any]]] = None,
        limit: int = 50,
    ) -> Dict[InventoryType, List[AgentInfo]]:
        """Search across multiple inventories."""
        
    def search_all(...) -> List[AgentInfo]:
        """Search all inventories and return flattened results."""
        
    def parse_inventory_types(
        self,
        type_strings: Optional[List[str]]
    ) -> Optional[List[InventoryType]]:
        """Parse inventory type strings to enum values."""


# Module-level singleton with default inventories
inventory_registry = get_inventory_registry()
```

**Usage**:

```python
from .helpers import inventory_registry, InventoryType

# Search specific inventories
results = inventory_registry.search(
    resources_service=resources_service,
    user_id=user_id,
    inventories=[InventoryType.A2A_AGENTS],
    capability_filter=["charting", "analytics"],
)

# Search all inventories
all_agents = inventory_registry.search_all(
    resources_service=resources_service,
    user_id=user_id,
    capability_filter=required_capabilities,
)
```

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

### Example 1: Mixed Custom and A2A Agents

For request: "Create a workflow to search Jira and generate analytics charts"

**Agent Selection Order** (Custom preferred over A2A):
1. Jira Agent (custom) selected first → covers "jira" capability
2. Analytics Agent (A2A) selected second → covers "analytics" capability (uncovered)

```json
{
  "name": "Jira & Analytics Workflow",
  "description": "Search Jira and generate analytics",
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
        "system_message": "Orchestrate Jira and Analytics workflow..."
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
      "rid": "existing_a2a_0_rid",
      "name": "Analytics Agent",
      "type": "a2a_agent_node",
      "config": {
        "type": "a2a_agent_node",
        "base_url": "http://analytics-agent:8080",
        "bearer_token": "secret-token"
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
    { "uid": "agent_1", "node": "existing_a2a_0_rid" },
    { "uid": "finalize", "node": "final_answer_node_rid" }
  ]
}
```

### Example 2: Custom Agent Reused + New Agent Created

For request: "Create a workflow to search Jira and Confluence"

**Agent Selection Order**:
1. Jira Agent (existing custom) selected first → covers "jira" capability
2. No A2A agents match "confluence" → skipped
3. Confluence Agent created from provider → covers "confluence" capability

```json
{
  "name": "Jira & Confluence Workflow",
  "description": "Search Jira and Confluence for information",
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
      "rid": "new_agent_0_rid",
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
    { "uid": "agent_1", "node": "new_agent_0_rid" },
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
| "Create a Jira search workflow" | Single custom agent with Jira MCP |
| "Create a workflow for Jira and Confluence" | Orchestrated 2-agent workflow |
| "Create a charting workflow" | Reuses existing A2A agent with charting skills |
| "Create a workflow for analytics and reporting" | Reuses A2A agent matching "analytics" capability |
| "Create a sales agent" | LLM-only agent for sales tasks |
| "Search Jira and generate charts" | Mixed: Custom + A2A agents |

### Expected Flow

1. **ANALYZE**: Identifies capabilities and orchestration needs
2. **SEARCH**: Finds LLM, providers, custom agents, and A2A agents (via InventoryRegistry)
3. **DESIGN**: Prioritizes Custom → A2A → New agents (one per capability), generates blueprint
4. **VALIDATE**: Validates, previews, saves to database

### Output

- New workflow blueprint saved to database
- New agents created in user's inventory (if needed)
- `blueprint_id` returned for immediate use

---

## Workflow Creation Rules

This section documents the **rules and decision logic** the builder follows when creating workflows.

### Rule 1: Agent Selection Priority

When building a workflow, agents are selected in this **strict priority order**. **Only ONE agent per capability type is selected**.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AGENT SELECTION PRIORITY                          │
│                                                                      │
│   Priority 1: Reuse BEST Custom Agent (PREFERRED)                    │
│   └─► Match agent's provider to required capabilities                │
│   └─► Agent only gets capabilities its provider actually matches     │
│   └─► Select agent with MOST matched capabilities                    │
│                                                                      │
│   Priority 2: Reuse BEST A2A Agent (for uncovered capabilities)      │
│   └─► Match skills from agent_card to UNCOVERED capabilities         │
│   └─► Uses SkillMatcher for flexible text matching                   │
│   └─► Select agent with MOST matched capabilities                    │
│                                                                      │
│   Priority 3: Create New Agent (with Provider)                       │
│   └─► For capabilities with matching providers but no existing agent │
│   └─► Creates new agent resource in user's inventory                 │
│                                                                      │
│   Priority 4: Create LLM-Only Agent                                  │
│   └─► For capabilities with no matching provider                     │
│   └─► Agent uses LLM reasoning only (no external tools)              │
└─────────────────────────────────────────────────────────────────────┘
```

**Agent Selection Behavior**:

| Scenario | Behavior |
|----------|----------|
| 2 custom agents matching same capability | 1 is added (best match by capability count) |
| 2 A2A agents matching same capability | 1 is added (best match by capability count) |
| 1 A2A + 1 Custom (same capability) | **Custom is added** (A2A skipped - custom preferred) |

**Why this order?**
- Custom agents are preferred - they are user-configured and run locally
- A2A agents are used for capabilities not covered by custom agents
- Only ONE agent per step prevents duplicate capability coverage
- Creating new agents adds to inventory - only when necessary
- LLM-only agents are the fallback when no tools are available

### Rule 2: Orchestrator Decision

The builder decides whether to add an orchestrator based on the **final agent count**:

```python
# Orchestrator is added when:
needs_orchestrator = (
    analysis.needs_orchestrator or    # LLM explicitly requested it
    final_agent_count > 1             # More than 1 agent in workflow
)
```

| Scenario | Agent Count | Orchestrator? |
|----------|-------------|---------------|
| "Create a Jira workflow" | 1 | ❌ No |
| "Create a Jira and Confluence workflow" | 2 | ✅ Yes |
| "Create a sales, marketing, and support workflow" | 3 | ✅ Yes |

**Important**: The orchestrator decision is made **AFTER** building agents, not before. This ensures:
- Single-agent workflows don't get unnecessary orchestrators
- The decision is based on actual agents selected, not search results

### Rule 3: Capability Matching

#### For Providers:
```python
# STRICT matching: capability must appear in provider name
if capability.lower() in provider.name.lower():
    provider.matched_capabilities.append(capability)
```

| Capability | Provider Name | Match? |
|------------|---------------|--------|
| "jira" | "Jira MCP" | ✅ Yes |
| "jira" | "Confluence MCP" | ❌ No |
| "sales" | "Salesforce Provider" | ✅ Yes |

#### For Custom Agents:
```python
# Agent inherits ONLY its provider's matched capabilities
agent.matched_capabilities = provider_caps_map[agent.provider_rid]
```

**Example**: If searching for `["jira", "sales"]`:
- Jira Provider matches `["jira"]`
- Jira Agent (with Jira Provider) gets `matched_capabilities: ["jira"]` only
- NOT `["jira", "sales"]` - prevents false capability claims

#### For A2A Agents:
```python
# Flexible matching using SkillMatcher across all metadata
searchable_text = " ".join([
    agent.name,
    agent_card.name,
    agent_card.description,
    *agent_card.skills,
    *agent_card.skill_descriptions,
    *agent_card.tags
])

matched = SkillMatcher.match_any(capabilities, searchable_text)
```

**SkillMatcher strategies**:
1. Direct substring match: `"chart"` in `"create_chart"` ✅
2. Compound word split: `"chart_generator"` → check `"chart"`, `"generator"`
3. Root word match: `"charting"` → `"chart"` (strips suffix)

### Rule 4: Blueprint Structure

Every generated workflow follows this structure:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MANDATORY NODES (Always Present)                  │
│                                                                      │
│   • user_question_node  ─── Entry point for user input              │
│   • final_answer_node   ─── Exit point for workflow response        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    CONDITIONAL NODES                                 │
│                                                                      │
│   • orchestrator_node   ─── Added when 2+ agents                    │
│   • router_direct       ─── Condition for orchestrator branching    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    AGENT NODES (1 or more)                           │
│                                                                      │
│   • custom_agent_node   ─── Local agent with LLM + optional provider │
│   • a2a_agent_node      ─── Remote agent via A2A protocol           │
└─────────────────────────────────────────────────────────────────────┘
```

### Rule 5: Execution Plan Patterns

#### Single Agent (No Orchestrator):
```
user_input → agent → finalize
```

```json
[
  { "uid": "user_input", "node": "user_question_node_rid" },
  { "uid": "agent", "node": "agent_rid" },
  { "uid": "finalize", "node": "final_answer_node_rid" }
]
```

#### Multiple Agents (With Orchestrator):
```
user_input → orchestrator ←→ [agents] → finalize
```

```json
[
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
  { "uid": "agent_0", "node": "agent_0_rid" },
  { "uid": "agent_1", "node": "agent_1_rid" },
  { "uid": "finalize", "node": "final_answer_node_rid" }
]
```

### Rule 6: Agent Node Configuration

#### Custom Agent Node:
```json
{
  "rid": "agent_rid",
  "name": "Jira Agent",
  "type": "custom_agent_node",
  "config": {
    "type": "custom_agent_node",
    "llm": "$ref:llm_rid",              // REQUIRED
    "system_message": "You are...",      // REQUIRED
    "provider": "$ref:provider_rid"      // Optional (MCP tools)
  }
}
```

#### A2A Agent Node:
```json
{
  "rid": "a2a_agent_rid",
  "name": "Analytics Agent",
  "type": "a2a_agent_node",
  "config": {
    "type": "a2a_agent_node",
    "base_url": "http://analytics:8080",  // REQUIRED
    "bearer_token": "secret"              // Optional
  }
}
```

### Rule 7: Capability Coverage

The builder ensures **all required capabilities are covered**:

```python
# After all agent selection steps:
missing_caps = required_capabilities - used_capabilities

# For any still-missing capability:
for cap in missing_caps:
    create_llm_only_agent(f"{cap.title()} Agent")
```

**Example**: Request for `["jira", "sales", "reporting"]`
1. Jira Agent reused → covers `"jira"`
2. No sales provider → creates "Sales Agent" (LLM-only)
3. No reporting provider → creates "Reporting Agent" (LLM-only)

### Decision Flow Summary

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         BUILDER DECISION FLOW                             │
└──────────────────────────────────────────────────────────────────────────┘

User Request: "Create a workflow for X and Y"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: ANALYZE                                                         │
│ ├─► Extract capabilities: ["x", "y"]                                     │
│ ├─► Determine needs_orchestrator: True (2 capabilities)                  │
│ └─► Suggested agent count: 2                                             │
└─────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SEARCH                                                          │
│ ├─► Find LLMs (REQUIRED - fail if none)                                  │
│ ├─► Find Providers matching "x" or "y"                                   │
│ ├─► Find Custom Agents with matching providers                           │
│ └─► Find A2A Agents with matching skills                                 │
└─────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: DESIGN (Only ONE agent per capability type)                     │
│                                                                          │
│ Step 1: Select BEST custom agent (PREFERRED)                             │
│ └─► Find custom agent with most matching capabilities → add to workflow  │
│                                                                          │
│ Step 2: Select BEST A2A agent (for UNCOVERED capabilities only)          │
│ └─► Find A2A agent matching uncovered capabilities → add to workflow     │
│                                                                          │
│ Step 3: Create agents for remaining providers                            │
│ └─► Providers with uncovered capabilities → create new agent             │
│                                                                          │
│ Step 4: Create LLM-only agents for missing capabilities                  │
│ └─► Remaining capabilities → create LLM-only agent                       │
│                                                                          │
│ Step 5: Determine orchestrator (AFTER building agents)                   │
│ └─► final_agent_count > 1 ? add orchestrator : no orchestrator           │
│                                                                          │
│ Step 6: Build execution plan                                             │
│ └─► Single agent pattern OR orchestrated pattern                         │
└─────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: VALIDATE & SAVE                                                 │
│ ├─► Validate blueprint structure                                         │
│ ├─► Check all node references                                            │
│ └─► Save to database → return blueprint_id                               │
└─────────────────────────────────────────────────────────────────────────┘
```

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

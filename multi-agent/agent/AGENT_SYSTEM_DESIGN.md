# UnifAI Agent System - Complete Design Specification

## Table of Contents

1. [Overview](#overview)
2. [Design Goals](#design-goals)
3. [Design Philosophy](#design-philosophy)
4. [High-Level Architecture](#high-level-architecture)
5. [Core Components](#core-components)
6. [Context System](#context-system)
7. [Strategy System](#strategy-system)
8. [Phase System (Optional)](#phase-system-optional)
9. [Execution Hooks](#execution-hooks)
10. [Agent IO (Streaming + HITL)](#agent-io-streaming--hitl)
11. [State Persistence](#state-persistence)
12. [Module Structure](#module-structure)
13. [Interfaces and Contracts](#interfaces-and-contracts)
14. [Implementation Guide](#implementation-guide)
15. [Usage Examples](#usage-examples)

---

## Overview

This document specifies the design for a **standalone agent library** that serves as the core foundation for the UnifAI multi-agent system. The agent library is designed to be:

- **Independent**: Can be used standalone or within the larger UnifAI ecosystem
- **Generic**: Core is phase-agnostic; phases are a strategy-level concern
- **Flexible**: Supports multiple execution strategies (ReAct, PlanAndExecute, custom phased)
- **Extensible**: Hook-based architecture for HITL, logging, retries, etc.
- **SOLID compliant**: Single responsibility, clean interfaces, dependency injection

### Current State

The existing codebase has agent functionality scattered across:
- `elements/nodes/common/agent/` - AgentRunner, strategies, phases, execution handlers
- `elements/nodes/orchestrator/` - OrchestratorNode with context builders
- `agent/` - Partial standalone agent implementation

### Target State

A unified `agent/` module that:
- Contains all agent primitives (BaseTool, BaseLLM, ChatMessage, etc.)
- Provides the core execution engine (AgentRunner, ToolExecutor)
- Supports sophisticated context control via policies and queries
- Handles streaming and HITL through unified AgentIO
- Is imported BY other modules (elements/tools, elements/llms, elements/nodes)

---

## Design Goals

```
+-------------------------------------------------------------------------+
|                           DESIGN GOALS                                   |
+-------------------------------------------------------------------------+
|                                                                          |
|  1. CONTEXT CONTROL                                                      |
|     - Precise control over what the LLM sees at each step               |
|     - Query-based filtering of conversation history                     |
|     - Dynamic context injection via providers                           |
|     - Token budget management                                           |
|                                                                          |
|  2. STRATEGY FLEXIBILITY                                                 |
|     - Support ReAct (simple loop, no phases)                            |
|     - Support PlanAndExecute (2 phases)                                 |
|     - Support custom phased strategies (N phases)                       |
|     - Strategies own their phase logic - core doesn't know about phases |
|                                                                          |
|  3. EXECUTION MODES                                                      |
|     - AUTO: No human intervention                                        |
|     - GUIDED: Human approves dangerous actions                          |
|     - MANUAL: Human approves every action                               |
|     - DRY_RUN: No actual execution                                       |
|                                                                          |
|  4. STREAMING AND HITL                                                   |
|     - Unified interface for output streaming and human input            |
|     - LLM token streaming to external consumers                         |
|     - Approval requests for HITL                                        |
|                                                                          |
|  5. STATE PERSISTENCE                                                    |
|     - Abstract state storage (in-memory, graph state, redis)            |
|     - Pause/resume execution                                            |
|     - State recovery                                                     |
|                                                                          |
|  6. OBSERVABILITY                                                        |
|     - Tracing via hooks                                                  |
|     - Step-by-step execution visibility                                 |
|                                                                          |
|  7. SOLID PRINCIPLES                                                     |
|     - Single Responsibility: Each component does one thing              |
|     - Open/Closed: Extend via hooks and strategies, not modification    |
|     - Dependency Inversion: Depend on protocols, not implementations    |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Design Philosophy

### Core Principle: Phase-Agnostic Core

The most important design decision is that the **core system knows nothing about phases**. Phases are a concern of specific strategies, not the execution engine.

```
+-------------------------------------------------------------------------+
|                         DESIGN PRINCIPLE                                 |
+-------------------------------------------------------------------------+
|                                                                          |
|  CORE SYSTEM:                                                            |
|    - MessageHistory with generic metadata                               |
|    - Query-based filtering (no phase awareness)                         |
|    - ContextPolicy defines what LLM sees                                |
|                                                                          |
|  STRATEGY LAYER (optional):                                              |
|    - Phased strategies ADD phase info to metadata                       |
|    - Phased strategies QUERY by phase when building context             |
|    - Non-phased strategies don't use phase metadata at all              |
|                                                                          |
|  +---------------------------------------------------------------------+ |
|  |                         CORE                                        | |
|  |  +---------------+  +---------------+  +---------------+            | |
|  |  |MessageHistory |  |ContextPolicy  |  |ContextBuilder |            | |
|  |  |               |  |               |  |               |            | |
|  |  | entries with  |  | query-based   |  | executes      |            | |
|  |  | metadata:Dict |  | filtering     |  | policy        |            | |
|  |  +---------------+  +---------------+  +---------------+            | |
|  |                                                                     | |
|  |  >>> Core knows NOTHING about phases <<<                            | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|                              ^                                           |
|                              | uses                                      |
|  +---------------------------+-------------------------------------+     |
|  |                      STRATEGIES                                 |     |
|  |                                                                 |     |
|  |  +-------------+    +-------------+    +-------------+          |     |
|  |  |  ReAct      |    |PlanExecute  |    |  Custom     |          |     |
|  |  |             |    |             |    |  Phased     |          |     |
|  |  | no phases   |    | 2 phases    |    | N phases    |          |     |
|  |  | simple query|    | adds phase  |    | adds phase  |          |     |
|  |  |             |    | to metadata |    | to metadata |          |     |
|  |  +-------------+    +-------------+    +-------------+          |     |
|  |                                                                 |     |
|  |  >>> Strategies decide IF and HOW to use metadata <<<           |     |
|  |                                                                 |     |
|  +-----------------------------------------------------------------+     |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Key Insights

1. **Context is Everything**: The LLM's behavior is entirely determined by what context it receives. Control the context, control the agent.

2. **History is Immutable, Context is a View**: MessageHistory is append-only. ContextPolicy defines a query/view over that history.

3. **Strategies Own Their Logic**: The runner asks the strategy for its policy and metadata. It doesn't interpret or modify.

4. **Hooks are Universal Extension**: HITL, logging, retries - all implemented as hooks. No special cases in core.

5. **Unified IO**: Streaming output and HITL input use the same interface (AgentIO).

---

## High-Level Architecture

```
+-------------------------------------------------------------------------+
|                      HIGH-LEVEL ARCHITECTURE                             |
+-------------------------------------------------------------------------+
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  |                         USER / SYSTEM                              |  |
|  |                              |                                     |  |
|  |                              v                                     |  |
|  |  +----------------------------------------------------------------+|  |
|  |  |                      AgentRunner                               ||  |
|  |  |                                                                ||  |
|  |  |   +-------------+  +-------------+  +-----------------+        ||  |
|  |  |   |  Strategy   |  |   Hooks     |  |    AgentIO      |        ||  |
|  |  |   |             |  |             |  |                 |        ||  |
|  |  |   | - think()   |  | - approval  |  | - streaming     |        ||  |
|  |  |   | - policy    |  | - logging   |  | - HITL input    |        ||  |
|  |  |   | - tools     |  | - retry     |  |                 |        ||  |
|  |  |   +------+------+  +------+------+  +--------+--------+        ||  |
|  |  |          |                |                  |                 ||  |
|  |  |          v                v                  v                 ||  |
|  |  |   +------------------------------------------------------------+|  |
|  |  |   |                  Execution Loop                            ||  |
|  |  |   |                                                            ||  |
|  |  |   |  1. Get policy from strategy                               ||  |
|  |  |   |  2. Build context (ContextBuilder + policy)                ||  |
|  |  |   |  3. Strategy thinks -> ThinkResult                         ||  |
|  |  |   |  4. Hooks process (approval, logging)                      ||  |
|  |  |   |  5. Execute tools (ToolExecutor)                           ||  |
|  |  |   |  6. Strategy provides metadata for entry                   ||  |
|  |  |   |  7. Append to history                                      ||  |
|  |  |   |  8. Repeat until should_continue = false                   ||  |
|  |  |   |                                                            ||  |
|  |  |   +------------------------------------------------------------+|  |
|  |  |                           |                                     |  |
|  |  +---------------------------+-------------------------------------+  |
|  |                              v                                        |
|  |  +----------------------------------------------------------------+   |
|  |  |                     Core Components                            |   |
|  |  |                                                                |   |
|  |  |  +--------------+  +--------------+  +--------------+          |   |
|  |  |  |MessageHistory|  |ContextBuilder|  | ToolExecutor |          |   |
|  |  |  |              |  |              |  |              |          |   |
|  |  |  | - entries    |  | - policy     |  | - execute    |          |   |
|  |  |  | - metadata   |  | - providers  |  | - tools      |          |   |
|  |  |  | - query      |  | - build()    |  |              |          |   |
|  |  |  +--------------+  +--------------+  +--------------+          |   |
|  |  |                                                                |   |
|  |  +----------------------------------------------------------------+   |
|  |                              |                                        |
|  |                              v                                        |
|  |  +----------------------------------------------------------------+   |
|  |  |                      Persistence                               |   |
|  |  |                                                                |   |
|  |  |  +--------------+  +--------------+  +--------------+          |   |
|  |  |  |  StateStore  |  |InMemoryStore |  | GraphStore   |          |   |
|  |  |  |  (protocol)  |  |              |  |              |          |   |
|  |  |  +--------------+  +--------------+  +--------------+          |   |
|  |  |                                                                |   |
|  |  +----------------------------------------------------------------+   |
|  |                                                                       |
|  +-----------------------------------------------------------------------+
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Core Components

### MessageHistory

The immutable, append-only store of all conversation entries.

```
+-------------------------------------------------------------------------+
|                         MessageHistory                                   |
|                   (Immutable, Append-Only)                              |
+-------------------------------------------------------------------------+
|                                                                          |
|  class MessageHistory:                                                   |
|      """Immutable conversation history."""                              |
|                                                                          |
|      _entries: Tuple[HistoryEntry, ...]                                 |
|                                                                          |
|      def append(self, entry: HistoryEntry) -> "MessageHistory":         |
|          """Return new history with entry appended."""                  |
|                                                                          |
|      def query(self, predicate: Callable[[HistoryEntry], bool])         |
|          -> List[HistoryEntry]:                                         |
|          """Filter entries by predicate."""                             |
|                                                                          |
|      def by_type(self, *types: EntryType) -> List[HistoryEntry]:        |
|          """Get entries of specific types."""                           |
|                                                                          |
|      def latest(self, n: int) -> List[HistoryEntry]:                    |
|          """Get last n entries."""                                      |
|                                                                          |
|      def slice(self, start: int, end: int) -> List[HistoryEntry]:       |
|          """Get entries in range."""                                    |
|                                                                          |
|      def __len__(self) -> int: ...                                      |
|      def __iter__(self) -> Iterator[HistoryEntry]: ...                  |
|                                                                          |
+-------------------------------------------------------------------------+
```

### HistoryEntry

A single entry in the conversation history.

```
+-------------------------------------------------------------------------+
|                          HistoryEntry                                    |
+-------------------------------------------------------------------------+
|                                                                          |
|  @dataclass(frozen=True)                                                 |
|  class HistoryEntry:                                                     |
|      id: str                      # Unique identifier (uuid)            |
|      timestamp: float             # When added (time.time())            |
|      entry_type: EntryType        # Type of entry                       |
|      role: Role                   # For ChatMessage conversion          |
|      content: str                 # Text content                        |
|      tool_calls: Tuple[ToolCall, ...] = ()  # If assistant with tools  |
|      tool_call_id: Optional[str] = None     # If tool response          |
|      metadata: Dict[str, Any] = field(default_factory=dict)             |
|                                   # ^^^ GENERIC - strategy decides      |
|                                                                          |
|  class EntryType(str, Enum):                                             |
|      SYSTEM = "system"            # System message                      |
|      USER = "user"                # User input                          |
|      ASSISTANT_TEXT = "assistant_text"    # Assistant text response    |
|      ASSISTANT_TOOL = "assistant_tool"    # Assistant tool call        |
|      TOOL_RESULT = "tool_result"  # Tool execution result               |
|      CONTEXT = "context"          # Injected context (from providers)  |
|      GUIDANCE = "guidance"        # Strategy guidance message           |
|                                                                          |
|  class Role(str, Enum):                                                  |
|      SYSTEM = "system"                                                   |
|      USER = "user"                                                       |
|      ASSISTANT = "assistant"                                             |
|      TOOL = "tool"                                                       |
|                                                                          |
|  METADATA EXAMPLES (strategy decides what to put):                       |
|    {"phase": "planning"}              # Phased strategy                 |
|    {"iteration": 3}                   # Any strategy                    |
|    {"source": "workplan_provider"}    # Context origin                  |
|    {"tool_name": "search"}            # Tool info                       |
|    {}                                 # Empty - totally fine            |
|                                                                          |
+-------------------------------------------------------------------------+
```

### ToolCall and ToolResult

```
+-------------------------------------------------------------------------+
|                      ToolCall and ToolResult                             |
+-------------------------------------------------------------------------+
|                                                                          |
|  @dataclass(frozen=True)                                                 |
|  class ToolCall:                                                         |
|      id: str                       # Unique call ID                     |
|      name: str                     # Tool name                          |
|      arguments: Dict[str, Any]     # Tool arguments                     |
|                                                                          |
|  @dataclass(frozen=True)                                                 |
|  class ToolResult:                                                       |
|      tool_call_id: str             # Matches ToolCall.id                |
|      content: str                  # Result content                     |
|      success: bool = True          # Whether execution succeeded        |
|      error: Optional[str] = None   # Error message if failed            |
|                                                                          |
+-------------------------------------------------------------------------+
```

### ChatMessage

For LLM interaction (conversion from HistoryEntry).

```
+-------------------------------------------------------------------------+
|                          ChatMessage                                     |
+-------------------------------------------------------------------------+
|                                                                          |
|  @dataclass(frozen=True)                                                 |
|  class ChatMessage:                                                      |
|      role: Role                                                          |
|      content: str                                                        |
|      tool_calls: Optional[List[ToolCall]] = None                        |
|      tool_call_id: Optional[str] = None                                 |
|                                                                          |
|  # Conversion from HistoryEntry                                          |
|  def entry_to_message(entry: HistoryEntry) -> ChatMessage:              |
|      return ChatMessage(                                                 |
|          role=entry.role,                                                |
|          content=entry.content,                                          |
|          tool_calls=list(entry.tool_calls) if entry.tool_calls else None|
|          tool_call_id=entry.tool_call_id                                |
|      )                                                                   |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Context System

The context system controls what the LLM sees at each step.

### EntryFilter

A composable predicate builder for filtering history entries.

```
+-------------------------------------------------------------------------+
|                          EntryFilter                                     |
|                  (Composable Predicate Builder)                         |
+-------------------------------------------------------------------------+
|                                                                          |
|  class EntryFilter:                                                      |
|      """Composable filter for history entries."""                       |
|                                                                          |
|      _predicate: Callable[[HistoryEntry], bool]                         |
|                                                                          |
|      # === CONSTRUCTORS ===                                              |
|                                                                          |
|      @staticmethod                                                       |
|      def all() -> "EntryFilter":                                        |
|          """Match all entries."""                                       |
|          return EntryFilter(lambda e: True)                             |
|                                                                          |
|      @staticmethod                                                       |
|      def none() -> "EntryFilter":                                       |
|          """Match no entries."""                                        |
|          return EntryFilter(lambda e: False)                            |
|                                                                          |
|      # === BY ENTRY TYPE ===                                             |
|                                                                          |
|      @staticmethod                                                       |
|      def by_type(*types: EntryType) -> "EntryFilter":                   |
|          """Match entries of given types."""                            |
|          type_set = set(types)                                           |
|          return EntryFilter(lambda e: e.entry_type in type_set)         |
|                                                                          |
|      # === BY METADATA (GENERIC) ===                                     |
|                                                                          |
|      @staticmethod                                                       |
|      def where(key: str, value: Any) -> "EntryFilter":                  |
|          """Match entries where metadata[key] == value."""              |
|          return EntryFilter(lambda e: e.metadata.get(key) == value)     |
|                                                                          |
|      @staticmethod                                                       |
|      def where_in(key: str, values: List[Any]) -> "EntryFilter":        |
|          """Match entries where metadata[key] in values."""             |
|          value_set = set(values)                                         |
|          return EntryFilter(lambda e: e.metadata.get(key) in value_set) |
|                                                                          |
|      @staticmethod                                                       |
|      def where_exists(key: str) -> "EntryFilter":                       |
|          """Match entries where metadata has key."""                    |
|          return EntryFilter(lambda e: key in e.metadata)                |
|                                                                          |
|      @staticmethod                                                       |
|      def where_missing(key: str) -> "EntryFilter":                      |
|          """Match entries where metadata lacks key."""                  |
|          return EntryFilter(lambda e: key not in e.metadata)            |
|                                                                          |
|      # === COMBINATORS ===                                               |
|                                                                          |
|      def and_(self, other: "EntryFilter") -> "EntryFilter":             |
|          """Logical AND."""                                              |
|          return EntryFilter(                                             |
|              lambda e: self._predicate(e) and other._predicate(e)       |
|          )                                                               |
|                                                                          |
|      def or_(self, other: "EntryFilter") -> "EntryFilter":              |
|          """Logical OR."""                                               |
|          return EntryFilter(                                             |
|              lambda e: self._predicate(e) or other._predicate(e)        |
|          )                                                               |
|                                                                          |
|      def not_(self) -> "EntryFilter":                                   |
|          """Logical NOT."""                                              |
|          return EntryFilter(lambda e: not self._predicate(e))           |
|                                                                          |
|      # === OPERATORS (syntactic sugar) ===                               |
|                                                                          |
|      def __and__(self, other): return self.and_(other)                  |
|      def __or__(self, other): return self.or_(other)                    |
|      def __invert__(self): return self.not_()                           |
|                                                                          |
|      # === CUSTOM ===                                                    |
|                                                                          |
|      @staticmethod                                                       |
|      def custom(fn: Callable[[HistoryEntry], bool]) -> "EntryFilter":   |
|          """Create filter from custom predicate."""                     |
|          return EntryFilter(fn)                                         |
|                                                                          |
|      # === APPLICATION ===                                               |
|                                                                          |
|      def apply(self, entries: Iterable[HistoryEntry])                   |
|          -> List[HistoryEntry]:                                         |
|          """Apply filter to entries."""                                 |
|          return [e for e in entries if self._predicate(e)]              |
|                                                                          |
|      def matches(self, entry: HistoryEntry) -> bool:                    |
|          """Check if entry matches filter."""                           |
|          return self._predicate(entry)                                  |
|                                                                          |
+-------------------------------------------------------------------------+
```

### ContextPolicy

Declarative rules for what the LLM sees.

```
+-------------------------------------------------------------------------+
|                         ContextPolicy                                    |
|                  (Declarative Query Rules)                              |
+-------------------------------------------------------------------------+
|                                                                          |
|  @dataclass                                                              |
|  class ContextPolicy:                                                    |
|      """Defines what context the LLM sees."""                           |
|                                                                          |
|      name: str                         # Policy identifier              |
|      include: EntryFilter              # What to include                |
|      exclude: Optional[EntryFilter] = None  # What to exclude           |
|      max_entries: Optional[int] = None # Limit entry count             |
|      max_tokens: Optional[int] = None  # Token budget                  |
|      prefer_recent: bool = True        # Prioritize recent entries     |
|      include_system: bool = True       # Always include system msg     |
|      context_providers: List[str] = field(default_factory=list)        |
|                                        # Dynamic context to inject      |
|                                                                          |
|  EXAMPLES:                                                               |
|                                                                          |
|  # ReAct: See everything                                                 |
|  react_policy = ContextPolicy(                                           |
|      name="react_full",                                                  |
|      include=EntryFilter.all()                                          |
|  )                                                                       |
|                                                                          |
|  # Minimal: Only user messages and tool results                          |
|  minimal_policy = ContextPolicy(                                         |
|      name="minimal",                                                     |
|      include=EntryFilter.by_type(EntryType.USER, EntryType.TOOL_RESULT),|
|      max_entries=20                                                      |
|  )                                                                       |
|                                                                          |
|  # Planning phase (phased strategy adds metadata["phase"])               |
|  planning_policy = ContextPolicy(                                        |
|      name="planning",                                                    |
|      include=(                                                           |
|          EntryFilter.by_type(EntryType.USER, EntryType.CONTEXT)         |
|          | EntryFilter.where("phase", "planning")                       |
|      ),                                                                  |
|      context_providers=["workplan", "adjacent_nodes"]                   |
|  )                                                                       |
|                                                                          |
|  # Execution phase: See planning results + current execution             |
|  execution_policy = ContextPolicy(                                       |
|      name="execution",                                                   |
|      include=(                                                           |
|          EntryFilter.by_type(EntryType.USER)                            |
|          | EntryFilter.where_in("phase", ["planning", "execution"])     |
|      ),                                                                  |
|      exclude=EntryFilter.by_type(EntryType.GUIDANCE),                   |
|      context_providers=["workplan"]                                     |
|  )                                                                       |
|                                                                          |
+-------------------------------------------------------------------------+
```

### ContextProvider

Dynamic context injection.

```
+-------------------------------------------------------------------------+
|                       ContextProvider                                    |
|                  (Dynamic Context Injection)                            |
+-------------------------------------------------------------------------+
|                                                                          |
|  class ContextProvider(Protocol):                                        |
|      """Provides dynamic context for injection."""                      |
|                                                                          |
|      @property                                                           |
|      def name(self) -> str:                                              |
|          """Provider identifier (used in policy.context_providers)."""  |
|          ...                                                             |
|                                                                          |
|      def get_context(self) -> str:                                       |
|          """Return context content to inject."""                        |
|          ...                                                             |
|                                                                          |
|      def get_metadata(self) -> Dict[str, Any]:                          |
|          """Return metadata for the injected entry."""                  |
|          return {"source": self.name}                                   |
|                                                                          |
|      def get_entry_type(self) -> EntryType:                             |
|          """Return entry type (usually CONTEXT)."""                     |
|          return EntryType.CONTEXT                                       |
|                                                                          |
|  # Built-in Providers                                                    |
|                                                                          |
|  class WorkPlanProvider(ContextProvider):                                |
|      """Provides current work plan state."""                            |
|      name = "workplan"                                                   |
|                                                                          |
|  class AdjacentNodesProvider(ContextProvider):                           |
|      """Provides available nodes for delegation."""                     |
|      name = "adjacent_nodes"                                             |
|                                                                          |
|  class ToolListProvider(ContextProvider):                                |
|      """Provides available tools description."""                        |
|      name = "tools"                                                      |
|                                                                          |
|  class SystemTimeProvider(ContextProvider):                              |
|      """Provides current timestamp."""                                  |
|      name = "system_time"                                                |
|                                                                          |
+-------------------------------------------------------------------------+
```

### ContextBuilder

Executes policy against history.

```
+-------------------------------------------------------------------------+
|                        ContextBuilder                                    |
|              (Executes Policy Against History)                          |
+-------------------------------------------------------------------------+
|                                                                          |
|  class ContextBuilder:                                                   |
|      """Builds context from history using policy."""                    |
|                                                                          |
|      def __init__(                                                       |
|          self,                                                           |
|          history: MessageHistory,                                        |
|          providers: Dict[str, ContextProvider] = None                   |
|      ): ...                                                              |
|                                                                          |
|      def register_provider(self, provider: ContextProvider) -> None:    |
|          """Register a context provider."""                             |
|                                                                          |
|      def build(self, policy: ContextPolicy) -> List[ChatMessage]:       |
|          """Build context according to policy."""                       |
|          # 1. Start with all entries                                     |
|          # 2. Apply include filter                                       |
|          # 3. Apply exclude filter                                       |
|          # 4. Apply max_entries with recency preference                  |
|          # 5. Inject context from providers                              |
|          # 6. Combine: system first, then providers, then history       |
|          # 7. Apply token budget (truncate if needed)                    |
|          # 8. Convert to ChatMessage list                                |
|                                                                          |
|      def update_history(self, history: MessageHistory) -> None:         |
|          """Update the history reference."""                            |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Strategy System

### AgentStrategy (ABC)

The core strategy contract.

```
+-------------------------------------------------------------------------+
|                        AgentStrategy                                     |
|                      (Abstract Base Class)                              |
+-------------------------------------------------------------------------+
|                                                                          |
|  class AgentStrategy(ABC):                                               |
|      """Base class for all agent strategies."""                         |
|                                                                          |
|      def __init__(self, llm: BaseLLM, tools: List[BaseTool]):           |
|          self._llm = llm                                                 |
|          self._tools = tools                                             |
|          self._iteration = 0                                             |
|                                                                          |
|      # === REQUIRED METHODS ===                                          |
|                                                                          |
|      @abstractmethod                                                     |
|      def think(self, context: List[ChatMessage]) -> ThinkResult:        |
|          """Given context, decide what to do next."""                   |
|                                                                          |
|      @abstractmethod                                                     |
|      def get_context_policy(self) -> ContextPolicy:                     |
|          """Return the policy for building context."""                  |
|                                                                          |
|      @abstractmethod                                                     |
|      def should_continue(self, history: MessageHistory) -> bool:        |
|          """Check if execution should continue."""                      |
|                                                                          |
|      # === OPTIONAL METHODS ===                                          |
|                                                                          |
|      def get_tools(self) -> List[BaseTool]:                             |
|          """Return available tools for current step."""                 |
|          return self._tools                                              |
|                                                                          |
|      def get_guidance(self) -> Optional[str]:                           |
|          """Return guidance message for LLM."""                         |
|          return None                                                     |
|                                                                          |
|      def on_step_complete(                                               |
|          self,                                                           |
|          action: AgentAction,                                            |
|          observation: ToolResult                                        |
|      ) -> Dict[str, Any]:                                               |
|          """Called after each step. Returns metadata for entry."""     |
|          self._iteration += 1                                            |
|          return {"iteration": self._iteration}                          |
|                                                                          |
|      def on_error(self, error: Exception) -> None:                      |
|          """Called when an error occurs."""                             |
|                                                                          |
|      def reset(self) -> None:                                           |
|          """Reset strategy state for new run."""                        |
|          self._iteration = 0                                             |
|                                                                          |
+-------------------------------------------------------------------------+
```

### ThinkResult

```
+-------------------------------------------------------------------------+
|                         ThinkResult                                      |
+-------------------------------------------------------------------------+
|                                                                          |
|  @dataclass                                                              |
|  class AgentAction:                                                      |
|      """A tool call to execute."""                                      |
|      tool: str                      # Tool name                         |
|      tool_input: Dict[str, Any]     # Tool arguments                    |
|      reasoning: str = ""            # Why this action                   |
|                                                                          |
|  @dataclass                                                              |
|  class AgentFinish:                                                      |
|      """Indicates agent is done."""                                     |
|      output: str                    # Final output                      |
|      reasoning: str = ""            # Why finishing                     |
|                                                                          |
|  @dataclass                                                              |
|  class ThinkResult:                                                      |
|      """Result of strategy.think()."""                                  |
|      actions: List[AgentAction] = field(default_factory=list)           |
|      finish: Optional[AgentFinish] = None                               |
|      reasoning: str = ""            # Overall reasoning                 |
|      metadata: Dict[str, Any] = field(default_factory=dict)             |
|                                                                          |
|      @property                                                           |
|      def is_done(self) -> bool:                                         |
|          return self.finish is not None                                 |
|                                                                          |
|      @property                                                           |
|      def has_actions(self) -> bool:                                     |
|          return len(self.actions) > 0                                   |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Strategy Implementations

```
+-------------------------------------------------------------------------+
|                     Strategy Implementations                             |
+-------------------------------------------------------------------------+
|                                                                          |
|  ReActStrategy:                                                          |
|      - No phases, simple loop                                           |
|      - Sees full history (EntryFilter.all())                            |
|      - on_step_complete returns {"iteration": N}                        |
|                                                                          |
|  PlanAndExecuteStrategy:                                                 |
|      - 2 phases: planning, execution                                    |
|      - Different policies per phase                                     |
|      - Different tools per phase                                        |
|      - on_step_complete returns {"phase": current_phase}                |
|                                                                          |
|  PhasedStrategy:                                                         |
|      - N phases via PhaseProvider                                       |
|      - Delegates to PhaseProvider for config                            |
|      - on_step_complete returns {"phase": current_phase}                |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Phase System (Optional)

Used only by strategies that need phases.

```
+-------------------------------------------------------------------------+
|                   Phase System (Strategy-Level)                          |
+-------------------------------------------------------------------------+
|                                                                          |
|  class PhaseProvider(Protocol):                                          |
|      """Provides phase configuration and manages transitions."""        |
|                                                                          |
|      def get_current_phase(self) -> str: ...                            |
|      def get_phase_config(self, phase: str) -> PhaseConfig: ...         |
|      def get_supported_phases(self) -> List[str]: ...                   |
|      def check_transition(self, action, observation) -> Optional[str]:...|
|      def transition_to(self, phase: str) -> None: ...                   |
|                                                                          |
|  @dataclass                                                              |
|  class PhaseConfig:                                                      |
|      name: str                          # Phase identifier              |
|      context_policy: ContextPolicy      # What LLM sees                 |
|      tools: List[BaseTool]              # Available tools               |
|      guidance: str = ""                 # Phase-specific prompt         |
|      max_iterations: int = 10           # Max iterations in phase       |
|                                                                          |
|  class TransitionPolicy(Protocol):                                       |
|      def should_transition(                                              |
|          self, current_phase, action, observation                       |
|      ) -> Optional[str]: ...                                            |
|                                                                          |
|  Implementations:                                                        |
|      ToolBasedTransition   - transition when specific tool called       |
|      IterationTransition   - transition after N iterations              |
|      CompositeTransition   - combine multiple policies                  |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Execution Hooks

```
+-------------------------------------------------------------------------+
|                        ExecutionHook                                     |
|                  (Chain of Responsibility)                              |
+-------------------------------------------------------------------------+
|                                                                          |
|  class HookDecision(Enum):                                               |
|      CONTINUE = "continue"      # Proceed normally                      |
|      PAUSE = "pause"            # Pause execution (wait for resume)     |
|      REJECT = "reject"          # Reject action, retry thinking         |
|      MODIFY = "modify"          # Use modified action                   |
|      ABORT = "abort"            # Abort entire execution                |
|                                                                          |
|  @dataclass                                                              |
|  class HookResult:                                                       |
|      decision: HookDecision                                              |
|      modified_result: Optional[ThinkResult] = None                      |
|      reason: str = ""                                                    |
|      data: Dict[str, Any] = field(default_factory=dict)                 |
|                                                                          |
|  class ExecutionHook(Protocol):                                          |
|      def before_action(self, result: ThinkResult) -> HookResult: ...    |
|      def after_action(self, result, observations) -> HookResult: ...    |
|      def on_error(self, error: Exception) -> HookResult: ...            |
|      def on_finish(self, result: AgentResult) -> None: ...              |
|                                                                          |
|  Built-in Hooks:                                                         |
|      ApprovalHook  - HITL via AgentIO                                   |
|      LoggingHook   - tracing                                             |
|      RetryHook     - error recovery                                      |
|                                                                          |
|  ApprovalPolicy:                                                         |
|      NEVER = "never"            # AUTO mode                             |
|      ALWAYS = "always"          # MANUAL mode                           |
|      DANGEROUS_ONLY = "dangerous"  # GUIDED mode                        |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Agent IO (Streaming + HITL)

```
+-------------------------------------------------------------------------+
|                           AgentIO                                        |
|                (Unified Streaming + HITL Interface)                     |
+-------------------------------------------------------------------------+
|                                                                          |
|  @dataclass                                                              |
|  class ApprovalResult:                                                   |
|      approved: bool                                                      |
|      modified_action: Optional[AgentAction] = None                      |
|      feedback: Optional[str] = None                                     |
|                                                                          |
|  class AgentIO(Protocol):                                                |
|      """Unified interface for streaming and HITL."""                    |
|                                                                          |
|      # === OUTPUT (Streaming) ===                                        |
|      def emit(self, event: str, data: Any) -> None: ...                 |
|      def emit_token(self, token: str) -> None: ...                      |
|      def emit_chunk(self, chunk: str) -> None: ...                      |
|      def emit_status(self, status: str) -> None: ...                    |
|                                                                          |
|      # === INPUT (HITL) ===                                              |
|      def request_approval(self, action: AgentAction) -> ApprovalResult:.|
|      def request_input(self, prompt: str) -> str: ...                   |
|      def request_choice(self, prompt, options) -> str: ...              |
|                                                                          |
|      # === LIFECYCLE ===                                                 |
|      def is_active(self) -> bool: ...                                   |
|      def close(self) -> None: ...                                       |
|                                                                          |
|  Implementations:                                                        |
|      NullIO       - No-op (AUTO mode)                                   |
|      ConsoleIO    - Terminal I/O                                        |
|      ChannelIO    - Wraps SessionChannel                                |
|      WebSocketIO  - Real-time web clients                               |
|      CompositeIO  - Multiple outputs                                    |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## State Persistence

```
+-------------------------------------------------------------------------+
|                          StateStore                                      |
|                 (Abstract State Persistence)                            |
+-------------------------------------------------------------------------+
|                                                                          |
|  class RunStatus(Enum):                                                  |
|      RUNNING = "running"                                                 |
|      PAUSED = "paused"                                                   |
|      COMPLETED = "completed"                                             |
|      FAILED = "failed"                                                   |
|      ABORTED = "aborted"                                                 |
|                                                                          |
|  @dataclass                                                              |
|  class AgentState:                                                       |
|      run_id: str                                                         |
|      history: MessageHistory                                             |
|      status: RunStatus                                                   |
|      iteration: int                                                      |
|      strategy_state: Dict[str, Any]                                     |
|      metadata: Dict[str, Any]                                           |
|      created_at: float                                                   |
|      updated_at: float                                                   |
|                                                                          |
|  class StateStore(Protocol):                                             |
|      def save(self, state: AgentState) -> None: ...                     |
|      def load(self, run_id: str) -> Optional[AgentState]: ...           |
|      def delete(self, run_id: str) -> None: ...                         |
|      def exists(self, run_id: str) -> bool: ...                         |
|      def list_runs(self, status: Optional[RunStatus]) -> List[str]: ... |
|                                                                          |
|  Implementations:                                                        |
|      InMemoryStateStore   - dict-based (default)                        |
|      GraphStateStore      - uses graph StateView (for nodes)            |
|      RedisStateStore      - Redis persistence                           |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## AgentRunner

```
+-------------------------------------------------------------------------+
|                         AgentRunner                                      |
|                    (Main Execution Engine)                              |
+-------------------------------------------------------------------------+
|                                                                          |
|  @dataclass                                                              |
|  class RunInput:                                                         |
|      query: str                                                          |
|      context: Optional[str] = None                                      |
|      run_id: Optional[str] = None                                       |
|      metadata: Dict[str, Any] = field(default_factory=dict)             |
|                                                                          |
|  @dataclass                                                              |
|  class AgentResult:                                                      |
|      output: str                                                         |
|      run_id: str                                                         |
|      status: RunStatus                                                   |
|      history: MessageHistory                                             |
|      iterations: int                                                     |
|      metadata: Dict[str, Any] = field(default_factory=dict)             |
|                                                                          |
|  class AgentRunner:                                                      |
|      def __init__(                                                       |
|          self,                                                           |
|          strategy: AgentStrategy,                                        |
|          executor: Optional[ToolExecutor] = None,                       |
|          context_builder: Optional[ContextBuilder] = None,              |
|          hooks: Optional[List[ExecutionHook]] = None,                   |
|          io: Optional[AgentIO] = None,                                  |
|          state_store: Optional[StateStore] = None,                      |
|          max_iterations: int = 50,                                       |
|          timeout: Optional[float] = None                                |
|      ): ...                                                              |
|                                                                          |
|      def run(self, input: RunInput) -> AgentResult: ...                 |
|      async def arun(self, input: RunInput) -> AgentResult: ...          |
|      def stream(self, input: RunInput) -> Iterator[Any]: ...            |
|      def resume(self, run_id: str) -> AgentResult: ...                  |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Execution Flow

```
+-------------------------------------------------------------------------+
|                       Execution Flow                                     |
+-------------------------------------------------------------------------+
|                                                                          |
|  1. Initialize or resume state                                          |
|  2. Add user input to history                                           |
|  3. Create context builder with history                                 |
|  4. Reset strategy                                                       |
|                                                                          |
|  5. Main loop while strategy.should_continue(history):                  |
|     a. Get context policy from strategy                                 |
|     b. Build context using policy                                       |
|     c. Add guidance if strategy provides                                |
|     d. Call strategy.think(context) -> ThinkResult                      |
|     e. If done, break                                                   |
|     f. Apply before_action hooks                                        |
|        - Handle ABORT, PAUSE, REJECT, MODIFY decisions                  |
|     g. Execute actions via ToolExecutor                                 |
|     h. Get metadata from strategy.on_step_complete()                    |
|     i. Append tool results to history with metadata                     |
|     j. Apply after_action hooks                                         |
|                                                                          |
|  6. Build and return AgentResult                                        |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## BaseTool and BaseLLM

```
+-------------------------------------------------------------------------+
|                      BaseTool and BaseLLM                                |
+-------------------------------------------------------------------------+
|                                                                          |
|  class BaseTool(ABC):                                                    |
|      name: str                                                           |
|      description: str                                                    |
|      args_schema: Optional[Type[BaseModel]] = None                      |
|                                                                          |
|      @abstractmethod                                                     |
|      def run(self, **kwargs: Any) -> Any: ...                           |
|                                                                          |
|      async def arun(self, **kwargs: Any) -> Any: ...                    |
|      def to_openai_schema(self) -> Dict[str, Any]: ...                  |
|                                                                          |
|  -----------------------------------------------------------------------  |
|                                                                          |
|  @dataclass                                                              |
|  class LLMResponse:                                                      |
|      content: str                                                        |
|      tool_calls: Optional[List[ToolCall]] = None                        |
|      usage: Optional[Dict[str, int]] = None                             |
|      raw: Any = None                                                     |
|                                                                          |
|  class BaseLLM(ABC):                                                     |
|      @abstractmethod                                                     |
|      def chat(self, messages, tools, **kwargs) -> LLMResponse: ...      |
|                                                                          |
|      @abstractmethod                                                     |
|      async def achat(self, messages, tools, **kwargs) -> LLMResponse:...|
|                                                                          |
|      def stream(self, messages, tools, **kwargs) -> Iterator[str]: ...  |
|      async def astream(self, ...) -> AsyncIterator[str]: ...            |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Module Structure

```
agent/
|-- __init__.py                   # Public API exports
|
|-- core/                         # Core execution (phase-agnostic)
|   |-- __init__.py
|   |-- runner.py                 # AgentRunner, RunInput, AgentResult
|   |-- executor.py               # ToolExecutor
|   +-- iterator.py               # AgentIterator (optional)
|
|-- models/                       # Data models
|   |-- __init__.py
|   |-- messages.py               # ChatMessage, Role, ToolCall
|   |-- history.py                # MessageHistory, HistoryEntry, EntryType
|   |-- actions.py                # AgentAction, AgentFinish, ThinkResult
|   +-- state.py                  # AgentState, RunStatus
|
|-- context/                      # Context management (phase-agnostic)
|   |-- __init__.py
|   |-- filter.py                 # EntryFilter
|   |-- policy.py                 # ContextPolicy
|   |-- builder.py                # ContextBuilder
|   +-- providers.py              # ContextProvider protocol + impls
|
|-- strategies/                   # Execution strategies
|   |-- __init__.py
|   |-- base.py                   # AgentStrategy ABC
|   |-- react.py                  # ReActStrategy
|   |-- plan_execute.py           # PlanAndExecuteStrategy
|   +-- phased.py                 # PhasedStrategy
|
|-- phases/                       # Phase support (strategy-level)
|   |-- __init__.py
|   |-- provider.py               # PhaseProvider protocol
|   |-- config.py                 # PhaseConfig
|   +-- transitions.py            # TransitionPolicy implementations
|
|-- hooks/                        # Execution hooks
|   |-- __init__.py
|   |-- base.py                   # ExecutionHook, HookDecision, HookResult
|   |-- approval.py               # ApprovalHook, ApprovalPolicy
|   |-- logging.py                # LoggingHook
|   +-- retry.py                  # RetryHook
|
|-- io/                           # I/O interfaces
|   |-- __init__.py
|   |-- base.py                   # AgentIO protocol, ApprovalResult
|   |-- null.py                   # NullIO
|   |-- console.py                # ConsoleIO
|   +-- channel.py                # ChannelIO (wraps SessionChannel)
|
|-- persistence/                  # State persistence
|   |-- __init__.py
|   |-- base.py                   # StateStore protocol
|   |-- memory.py                 # InMemoryStateStore
|   +-- graph.py                  # GraphStateStore
|
|-- tools/                        # Tool primitives
|   |-- __init__.py
|   +-- base.py                   # BaseTool ABC
|
|-- llm/                          # LLM primitives
|   |-- __init__.py
|   +-- base.py                   # BaseLLM ABC, LLMResponse
|
+-- tracing/                      # Observability
    |-- __init__.py
    |-- tracer.py                 # AgentTracer
    +-- events.py                 # TraceEvent types
```

---

## Implementation Guide

### Phase 1: Core Models
1. Create `agent/models/messages.py` - Role, ToolCall, ChatMessage
2. Create `agent/models/history.py` - EntryType, HistoryEntry, MessageHistory
3. Create `agent/models/actions.py` - AgentAction, AgentFinish, ThinkResult
4. Create `agent/models/state.py` - RunStatus, AgentState

### Phase 2: Context System
5. Create `agent/context/filter.py` - EntryFilter
6. Create `agent/context/policy.py` - ContextPolicy
7. Create `agent/context/providers.py` - ContextProvider protocol + impls
8. Create `agent/context/builder.py` - ContextBuilder

### Phase 3: Tools and LLM
9. Create `agent/tools/base.py` - BaseTool ABC
10. Create `agent/llm/base.py` - LLMResponse, BaseLLM ABC

### Phase 4: Hooks and IO
11. Create `agent/hooks/base.py` - HookDecision, HookResult, ExecutionHook
12. Create `agent/hooks/approval.py` - ApprovalPolicy, ApprovalHook
13. Create `agent/hooks/logging.py` - LoggingHook
14. Create `agent/io/base.py` - ApprovalResult, AgentIO
15. Create `agent/io/null.py` - NullIO
16. Create `agent/io/console.py` - ConsoleIO

### Phase 5: Strategies
17. Create `agent/strategies/base.py` - AgentStrategy ABC
18. Create `agent/strategies/react.py` - ReActStrategy
19. Create `agent/strategies/plan_execute.py` - PlanAndExecuteStrategy
20. Create `agent/phases/` module - PhaseProvider, PhaseConfig, transitions
21. Create `agent/strategies/phased.py` - PhasedStrategy

### Phase 6: Execution
22. Create `agent/core/executor.py` - ToolExecutor
23. Create `agent/core/runner.py` - RunInput, AgentResult, AgentRunner

### Phase 7: Persistence
24. Create `agent/persistence/base.py` - StateStore protocol
25. Create `agent/persistence/memory.py` - InMemoryStateStore

### Phase 8: Integration
26. Update `agent/__init__.py` - Export all public API
27. Update `elements/` to import from `agent/`

### Phase 9: Testing
28. Create tests for each module

---

## Usage Examples

### Simple ReAct Agent

```python
from agent import AgentRunner, ReActStrategy, ConsoleIO
from agent.tools import BaseTool

class SearchTool(BaseTool):
    name = "search"
    description = "Search the web"
    def run(self, query: str) -> str:
        return f"Results for: {query}"

runner = AgentRunner(
    strategy=ReActStrategy(
        llm=my_llm,
        tools=[SearchTool()],
        max_iterations=10
    ),
    io=ConsoleIO()
)

result = runner.run(RunInput(query="What is the capital of France?"))
```

### PlanAndExecute with Custom Policies

```python
from agent import AgentRunner, PlanAndExecuteStrategy
from agent.context import ContextPolicy, EntryFilter, EntryType

planning_policy = ContextPolicy(
    name="planning",
    include=EntryFilter.by_type(EntryType.USER, EntryType.CONTEXT),
    context_providers=["workplan"]
)

execution_policy = ContextPolicy(
    name="execution",
    include=(
        EntryFilter.by_type(EntryType.USER)
        | EntryFilter.where_in("phase", ["planning", "execution"])
    )
)

runner = AgentRunner(
    strategy=PlanAndExecuteStrategy(
        llm=my_llm,
        planning_tools=[plan_tool],
        execution_tools=[execute_tool],
        planning_policy=planning_policy,
        execution_policy=execution_policy
    )
)
```

### HITL with Approval Hook

```python
from agent import AgentRunner, ReActStrategy
from agent.hooks import ApprovalHook, ApprovalPolicy
from agent.io import ConsoleIO

runner = AgentRunner(
    strategy=ReActStrategy(llm=my_llm, tools=my_tools),
    io=ConsoleIO(),
    hooks=[
        ApprovalHook(
            io=ConsoleIO(),
            policy=ApprovalPolicy.DANGEROUS_ONLY,
            dangerous_tools={"delete_file", "execute_code"}
        )
    ]
)
```

---

## Key Design Decisions

1. **Core is Phase-Agnostic**: MessageHistory, ContextPolicy, ContextBuilder, AgentRunner know nothing about phases.

2. **Strategies Own Phase Logic**: Strategy decides what policy to return and what metadata to attach.

3. **Metadata is Generic**: `HistoryEntry.metadata: Dict[str, Any]` - strategy decides contents.

4. **Query-Based Filtering**: `EntryFilter` provides composable predicates for any filtering need.

5. **PhaseProvider is Optional**: Only used by `PhasedStrategy`, not by core.

6. **Hooks for Everything**: HITL, logging, retries all implemented as hooks.

7. **Unified AgentIO**: Single interface for streaming output and HITL input.

8. **Agent is Core Library**: All primitives live in `agent/`, other modules import from it.

---

## Migration Notes

1. Move `BaseTool` to `agent/tools/base.py`, update imports
2. Move `BaseLLM` to `agent/llm/base.py`, update imports
3. Move `ChatMessage`, `Role`, `ToolCall` to `agent/models/messages.py`
4. Refactor `elements/nodes/common/agent/` to use new agent module
5. Update orchestrator node to use new `PhasedStrategy`

---

*This document is the complete specification for the UnifAI Agent System.*

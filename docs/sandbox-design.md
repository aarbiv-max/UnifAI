# PHASE 1: DESIGN (Revision 4) — Agent Sandbox (Code Execution Environment)

## 1. Overview

### Problem Statement

Agents need an isolated, persistent environment to execute code (Python scripts, git operations, shell commands) on a user-provided OpenShift cluster. Today there is no sandbox infrastructure — agents can only interact with external systems via stateless tools (`oc_exec`, `ssh_exec`). There is no mechanism to provision per-agent pods, persist filesystem state across sessions, or manage sandbox lifecycle tied to workflow execution.

### Proposed Solution

Introduce a `sandbox_exec` tool that users configure with their OpenShift cluster credentials and a git repository. When a workflow starts, the system provisions one sandbox pod per agent node on the user's cluster, backed by a shared PVC (keyed by `run_id`). Agents send serial commands to their sandbox throughout the workflow. Temporal heartbeats monitor sandbox health. On workflow completion, cancellation, or crash, all sandbox pods are torn down while the PVC is preserved for future sessions.

### Success Criteria

- User can add `sandbox_exec` as a tool resource via the existing resource API (`resource.save`)
- Sandbox pods are provisioned per-agent before graph execution begins
- Agents can execute commands in their sandbox and receive stdout/stderr
- PVC persists across sessions; re-triggering a session reattaches the existing PVC
- Multi-agent workflows get separate pods with git worktrees on a shared PVC
- Sandbox pods are cleaned up on workflow completion, failure, or cancellation (no zombie pods)
- PVC is never deleted by the system (user data preserved)

---

## 2. Affected Components

| Layer | Component | Action | File Path |
|-------|-----------|--------|-----------|
| Domain | `SandboxExecTool` | New | `multi-agent/lib/mas/elements/tools/sandbox_exec/sandbox_exec.py` |
| Domain | `SandboxExecToolConfig` | New | `multi-agent/lib/mas/elements/tools/sandbox_exec/config.py` |
| Domain | `Identifier` / `META` | New | `multi-agent/lib/mas/elements/tools/sandbox_exec/identifiers.py` |
| Domain | `SandboxExecToolElementSpec` | New | `multi-agent/lib/mas/elements/tools/sandbox_exec/spec/spec.py` |
| Domain | `SandboxExecToolFactory` | New | `multi-agent/lib/mas/elements/tools/sandbox_exec/sandbox_exec_factory.py` |
| Domain | `SandboxExecToolValidator` | New | `multi-agent/lib/mas/elements/tools/sandbox_exec/validator.py` |
| Domain | `SandboxManagerPort` | New | `multi-agent/lib/mas/elements/tools/sandbox_exec/ports.py` |
| Domain | `SandboxPodInfo` / `SandboxState` | New | `multi-agent/lib/mas/elements/tools/sandbox_exec/models.py` |
| Domain | `SessionRecord` | Modified | `multi-agent/lib/mas/session/domain/session_record.py` |
| Domain | `ExecutionContext` | Modified | `multi-agent/lib/mas/core/execution_context.py` |
| Application | `SandboxLifecycleService` | New | `multi-agent/lib/mas/elements/tools/sandbox_exec/service.py` |
| Adapter (outbound) | `OpenShiftSandboxManager` | New | `multi-agent/adapters/outbound/openshift/sandbox_manager.py` |
| Adapter (outbound) | `TemporalSessionSubmitter` | Modified | `multi-agent/adapters/outbound/temporal/submitter.py` |
| Adapter (temporal/models) | `SessionWorkflowParams` | Modified | `multi-agent/adapters/temporal/models.py` |
| Adapter (temporal/models) | `ProvisionSandboxParams` / `TeardownSandboxParams` | New | `multi-agent/adapters/temporal/models.py` |
| Adapter (inbound/temporal) | `SessionWorkflow` | Modified | `multi-agent/adapters/inbound/temporal/workflows/session_workflow.py` |
| Adapter (inbound/temporal) | `SandboxLifecycleActivities` | New | `multi-agent/adapters/inbound/temporal/activities/sandbox_activities.py` |
| Adapter (inbound/temporal) | Temporal worker registration | Modified | `multi-agent/adapters/inbound/temporal/worker.py` |
| Adapter (inbound/temporal) | `GraphNodeActivities` | Modified | `multi-agent/adapters/inbound/temporal/activities/graph_node_activities.py` |
| Application | `BackgroundSessionRunner` | Modified | `multi-agent/lib/mas/session/execution/background_runner.py` |
| Application | `BackgroundSessionOps` | Modified | `multi-agent/lib/mas/session/execution/background_runner.py` |
| Application | `BackgroundLifecycleHandler` | Modified | `multi-agent/lib/mas/session/execution/lifecycle_handler.py` |
| Application | `ToolsSpec` union | Modified | `multi-agent/lib/mas/elements/tools/types.py` |
| Application | `ElementDeps` | Modified | `multi-agent/lib/mas/core/element_deps.py` |
| Engine | `NodeExecutor` | Modified | `multi-agent/lib/mas/engine/distributed/node_executor.py` |
| Application | `WorkflowSessionFactory` | Modified | `multi-agent/lib/mas/session/building/workflow_session_factory.py` |
| Bootstrap | `AppContainer` | Modified | `multi-agent/bootstrap/container.py` |
| Infra | `Dockerfile.sandbox` | New | `multi-agent/Dockerfile.sandbox` |

---

## 3. Technical Design

### 3.1 Tool Element — `sandbox_exec`

Follows the exact pattern of `oc_exec` and `ssh_exec`: identifiers → config → tool → factory → validator → spec.

#### `identifiers.py`

```python
class Identifier(str, Enum):
    TYPE = "sandbox_exec"

META = Meta(
    name="Sandbox Exec",
    description="Execute commands in an isolated sandbox pod on an OpenShift cluster",
    tags=["tool", "sandbox", "exec", "openshift", "code", "execution"],
)
```

#### `config.py` — `SandboxExecToolConfig`

```python
class SandboxExecToolConfig(BaseToolConfig):
    type: Literal["sandbox_exec"] = "sandbox_exec"
    cluster_api: str          # OpenShift API endpoint (SecretHint)
    cluster_token: str        # auth token (SecretHint)
    namespace: str            # target namespace
    git_repo_url: str         # repo to clone on first provision
    git_token: str = ""       # token for private repo auth (SecretHint, optional)
    skip_tls_verify: bool = False
```

- **Purpose**: Configuration schema for the sandbox tool. Surfaces as a dynamic form in the UI catalog via `model_json_schema()`.
- **`git_token`**: Optional. If provided, used for HTTPS-based git clone authentication (`https://{git_token}@github.com/...`). Empty string means public repo.
- **`container_image`**: Removed from config — fixed at the adapter level (not user-configurable).
- **Dependencies**: `BaseToolConfig`

#### `sandbox_exec.py` — `SandboxExecTool`

```python
class SandboxCommandInput(BaseModel):
    cmd: str = Field(..., description="Shell command to execute in the sandbox")
    workdir: Optional[str] = Field(None, description="Working directory override")

class SandboxExecTool(BaseTool):
    name: str = "sandbox_exec"
    description: str = "Execute a command in the sandbox pod"
    args_schema = SandboxCommandInput

    def __init__(
        self, *,
        sandbox_manager: SandboxManagerPort,
        config: SandboxExecToolConfig,
        execution_ctx: ExecutionContextHolder,
    ): ...

    def run(self, *args, **kwargs) -> str:
        """
        1. Resolve node_uid from execution_ctx.context.tags["node_uid"]
        2. Resolve run_id from execution_ctx.context.tags["run_id"]
        3. Derive pod_name = f"sandbox-{run_id[:8]}-{node_uid}"
        4. Derive workdir = f"/workspace/worktree-{node_uid}"
        5. Delegate to sandbox_manager.execute(pod_name, namespace, ...)
        6. Return stdout/stderr
        """
```

- **Purpose**: The LLM-callable tool. Delegates execution to `SandboxManagerPort.execute()`.
- **Key design**: Pod identity is resolved **at call time** from `ExecutionContext.tags`, not at build time. This means one `SandboxExecTool` instance per resource works correctly for all agent nodes — each node's `StepContext.uid` is injected into `ExecutionContext.tags["node_uid"]` by `NodeExecutor` before the node runs (see §3.6).
- **Dependencies**: `SandboxManagerPort` (port), `SandboxExecToolConfig` (for cluster/namespace), `ExecutionContextHolder` (for runtime identity)

#### `sandbox_exec_factory.py` — `SandboxExecToolFactory`

```python
class SandboxExecToolFactory(BaseFactory[SandboxExecToolConfig, SandboxExecTool]):
    def accepts(self, cfg: SandboxExecToolConfig, element_type: str) -> bool:
        return element_type == Identifier.TYPE

    def create(self, cfg: SandboxExecToolConfig, **kwargs) -> SandboxExecTool:
        deps: ElementDeps | None = kwargs.get("deps")
        return SandboxExecTool(
            sandbox_manager=deps.sandbox_manager if deps else None,
            config=cfg,
            execution_ctx=deps.execution_ctx if deps else None,
        )
```

- **Purpose**: Creates tool instances. Reads `sandbox_manager` and `execution_ctx` from `deps` (the `ElementDeps` instance), following the same pattern as `SlackRetrieverFactory` which reads `deps.execution_ctx`.
- **No `ToolBuilder._extra_kwargs` override needed.** `CategoryBuilder._create_instance` already calls `factory.create(validated, deps=deps, **extra)`, so `deps` is available in `kwargs`.

#### `validator.py` — `SandboxExecToolValidator`

```python
class SandboxExecToolValidator(BaseElementValidator):
    def validate(self, config: SandboxExecToolConfig, context: ValidationContext) -> ValidatorReport:
        # 1. Validate cluster connectivity using oc context manager pattern
        #    (shared with OcExecTool — extract to utility if desired)
        # 2. Validate namespace exists: oc.invoke('get', ['namespace', config.namespace])
        # 3. Return CONNECTION_OK or appropriate error codes
```

- **Purpose**: Validates cluster reachability and namespace access when user saves the tool resource.

#### `spec/spec.py`

```python
class SandboxExecToolElementSpec(BaseElementSpec):
    category = ResourceCategory.TOOL
    type_key = Identifier.TYPE
    name = META.name
    description = META.description
    config_schema = SandboxExecToolConfig
    factory_cls = SandboxExecToolFactory
    tags = META.tags
    validator_cls = SandboxExecToolValidator
```

#### `types.py` modification

Add `SandboxExecToolConfig` to the `ToolsSpec` discriminated union:

```python
ToolsSpec = Annotated[
    Union[
        SshExecToolConfig,
        McpProxyToolConfig,
        OcExecToolConfig,
        WebFetchToolConfig,
        SandboxExecToolConfig,  # NEW
    ],
    Field(discriminator="type")
]
```

---

### 3.2 Domain — Sandbox Models & Port

All sandbox domain types live inside the tool module at `lib/mas/elements/tools/sandbox_exec/`, consistent with how each tool owns its internal models.

#### `models.py` — Runtime Models (not persisted)

```python
class SandboxPodInfo(BaseModel):
    """Ephemeral pod state — lives only in Temporal workflow state."""
    agent_id: str
    pod_name: str
    namespace: str
    worktree_path: str
    branch_name: str
    status: Literal["provisioning", "ready", "terminated", "failed"]

class SandboxState(BaseModel):
    """Runtime sandbox state — held by Temporal workflow, not persisted to DB."""
    session_id: str
    pvc_name: str
    cluster_api: str
    namespace: str
    git_repo_url: str
    pods: Dict[str, SandboxPodInfo] = {}  # keyed by agent_id
```

- **Purpose**: Runtime state during workflow execution. Held in Temporal workflow instance variables (`self._sandbox_state`). NOT persisted to any database.

#### `ports.py` — `SandboxManagerPort`

```python
class SandboxManagerPort(ABC):
    @abstractmethod
    def provision_pvc(
        self, pvc_name: str, namespace: str, cluster_api: str, token: str,
        skip_tls_verify: bool = False,
    ) -> None:
        """Create PVC (2Gi, RWX) if it doesn't exist. Idempotent."""
        ...

    @abstractmethod
    def provision_pod(
        self, pod_name: str, pvc_name: str, namespace: str,
        cluster_api: str, token: str,
        git_repo_url: str, worktree_path: str, branch_name: str,
        git_token: str = "",
        skip_tls_verify: bool = False,
    ) -> None:
        """Create pod (fixed image, 500m/512Mi req, 2/2Gi limit), mount PVC, set up git worktree. Idempotent."""
        ...

    @abstractmethod
    def execute(
        self, pod_name: str, namespace: str,
        cluster_api: str, token: str, cmd: str,
        workdir: Optional[str] = None,
        skip_tls_verify: bool = False,
    ) -> str:
        """Exec a command in a pod, return stdout/stderr."""
        ...

    @abstractmethod
    def teardown_pod(
        self, pod_name: str, namespace: str,
        cluster_api: str, token: str,
        skip_tls_verify: bool = False,
    ) -> None:
        """Delete a single pod. Idempotent (--ignore-not-found)."""
        ...

    @abstractmethod
    def is_pod_alive(
        self, pod_name: str, namespace: str,
        cluster_api: str, token: str,
        skip_tls_verify: bool = False,
    ) -> bool:
        """Health check — returns True if pod phase is Running."""
        ...
```

- **Dependencies**: None (pure port).
- **Stateless**: All cluster/auth info passed per-call.

---

### 3.3 Persistence — `SessionRecord.sandbox_pvc_name`

```python
class SessionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    run_id: str
    user_id: str
    blueprint_id: str
    run_context: ExecutionContext
    metadata: SessionMeta = Field(default_factory=SessionMeta)
    graph_state: GraphState = Field(default_factory=GraphState)
    status: SessionStatus = SessionStatus.PENDING
    sandbox_pvc_name: Optional[str] = None  # NEW

    def update_context(self, **updates) -> None:
        self.run_context = self.run_context.model_copy(update=updates)
```

- **No new collection.** Saved to the existing `workflow_sessions` document.
- **Backward compatible.** `extra="ignore"` means existing documents without this field deserialize as `None`.
- **Set once.** Written during `provision_sandboxes` activity via `repo.save(record)`.

### Deterministic Naming Convention

```
PVC name:   sandbox-pvc-{run_id[:8]}
Pod name:   sandbox-{run_id[:8]}-{node_uid}
Worktree:   /workspace/worktree-{node_uid}
Branch:     sandbox/{node_uid}
```

`node_uid` comes from `StepContext.uid` (the graph node identifier, e.g. `"agent_1"`, `"code_reviewer"`). This is the same value as `BaseNode.uid` / `CustomAgentNode.uid`.

---

### 3.4 Runtime Identity — How `run_id` and `node_uid` reach the tool

This is the critical plumbing that makes multi-agent sandbox isolation work.

#### Problem

`SandboxExecTool.run()` needs `run_id` (to derive pod name) and `node_uid` (to pick the correct pod). Today, neither value reaches tools at runtime:
- `run_id` is on `ExecuteNodeParams.session_id` but stops at `GraphNodeActivities` (used only for channel creation).
- `node_uid` is on `ExecuteNodeParams.node_uid` and injected into the node via `StepContext`, but not into tools.

#### Solution: Extend `ExecutionContext.tags`

`ExecutionContext.tags` is already `Dict[str, Any]` and is designed for extensible runtime metadata. `NodeExecutor` already sets `ExecutionContext` on the holder. The fix is to enrich it with `run_id` and `node_uid` before node execution:

##### Modified `NodeExecutor.execute_node` signature

Add `session_id` as an explicit parameter. This is **thread-safe** — the worker runs activities concurrently via `ThreadPoolExecutor`, so shared mutable state on the executor would race. Each activity call passes its own `params.session_id` directly.

```python
class NodeExecutor:
    def __init__(self, session_factory: WorkflowSessionFactory) -> None:
        self._factory = session_factory

    def execute_node(
        self,
        node_uid: str,
        node_blueprint: Dict[str, Any],
        step_context: Optional[StepContext],
        state: GraphState,
        channel: Optional[SessionChannel] = None,
        execution_context: Optional[ExecutionContext] = None,
        session_id: str = "",  # NEW — explicit, thread-safe parameter
    ) -> GraphState:
        mini_bp = BlueprintSpec.model_validate(node_blueprint)
        ctx_holder = ExecutionContextHolder()
        rt_plan = self._factory.build_runtime_plan(mini_bp, ctx_holder=ctx_holder)

        if execution_context:
            enriched = execution_context.model_copy(update={
                "tags": {
                    **execution_context.tags,
                    "run_id": session_id,      # from activity params
                    "node_uid": node_uid,      # the graph node id
                }
            })
            ctx_holder.context = enriched

        step = rt_plan.get_step(node_uid)
        if step_context:
            step.func.set_context(step_context)
        if channel and hasattr(step.func, "set_streaming_channel"):
            step.func.set_streaming_channel(channel)
        return step.func(state, config={})
```

##### Modified `GraphNodeActivities.execute_node`

Pass `session_id` as an explicit parameter — no shared mutable state:

```python
@activity.defn(name="execute_graph_node")
def execute_node(self, params: ExecuteNodeParams) -> GraphState:
    channel = None
    if self._channel_factory and params.session_id:
        channel = self._channel_factory.create(params.session_id)

    return self._executor.execute_node(
        node_uid=params.node_uid,
        node_blueprint=params.node_blueprint,
        step_context=params.step_context,
        state=params.state,
        channel=channel,
        execution_context=params.execution_context,
        session_id=params.session_id,  # NEW — passed per-call, thread-safe
    )
```

**Thread-safety**: `NodeExecutor` has no mutable instance state. Each `execute_node` call receives all identity via parameters. Multiple concurrent activities on the same worker are safe.

##### How the tool reads it

```python
class SandboxExecTool(BaseTool):
    def run(self, *args, **kwargs) -> str:
        ctx = self._execution_ctx.context  # ExecutionContextHolder → ExecutionContext
        run_id = ctx.tags["run_id"]
        node_uid = ctx.tags["node_uid"]
        pod_name = f"sandbox-{run_id[:8]}-{node_uid}"
        workdir = f"/workspace/worktree-{node_uid}"
        # delegate to sandbox_manager.execute(...)
```

This is the same holder pattern `SlackRetriever` uses to read `scope` and `user_id` at call time.

---

### 3.5 Application — `SandboxLifecycleService`

```python
class SandboxLifecycleService:
    def __init__(self, sandbox_manager: SandboxManagerPort): ...

    def provision_for_session(
        self,
        run_id: str,
        agent_ids: List[str],
        config: SandboxExecToolConfig,
        existing_pvc_name: Optional[str] = None,
    ) -> SandboxState:
        """
        1. Determine PVC name:
           - If existing_pvc_name is set (re-trigger): reuse it
           - Else: generate as f"sandbox-pvc-{run_id[:8]}"
        2. Call sandbox_manager.provision_pvc() — idempotent (2Gi, RWX)
        3. Detect and delete orphan pods from prior crashed runs
           (deterministic names — same pod names would collide)
        4. For each agent_id:
           - pod_name = f"sandbox-{run_id[:8]}-{agent_id}"
           - worktree_path = f"/workspace/worktree-{agent_id}"
           - branch_name = f"sandbox/{agent_id}"
           - Call sandbox_manager.provision_pod(git_token=config.git_token) — idempotent
             (fixed image + resource limits applied by adapter)
        5. Return SandboxState with all pod info
        """

    def teardown_for_session(
        self,
        sandbox_state: SandboxState,
        config: SandboxExecToolConfig,
    ) -> None:
        """
        1. For each pod in sandbox_state.pods:
           - Call sandbox_manager.teardown_pod() — idempotent
        2. Do NOT delete PVC
        """

    def teardown_by_naming(
        self,
        run_id: str,
        agent_ids: List[str],
        config: SandboxExecToolConfig,
    ) -> None:
        """
        Fallback teardown using deterministic naming (crash recovery).
        Reconstructs pod names from run_id + agent_ids, deletes each.
        """

    def health_check(
        self,
        sandbox_state: SandboxState,
        config: SandboxExecToolConfig,
    ) -> Dict[str, bool]:
        """Per-agent pod health check. Returns {agent_id: is_alive}."""
```

- **Purpose**: Application-layer orchestration of sandbox lifecycle.
- **Dependencies**: `SandboxManagerPort` only.

---

### 3.6 Outbound Adapter — `OpenShiftSandboxManager`

```python
SANDBOX_IMAGE = "quay.io/<org>/sandbox-base:latest"  # fixed, not user-configurable
PVC_SIZE = "2Gi"
POD_RESOURCES = {
    "requests": {"cpu": "500m", "memory": "512Mi"},
    "limits": {"cpu": "2", "memory": "2Gi"},
}

class OpenShiftSandboxManager(SandboxManagerPort):
    """Implements SandboxManagerPort using openshift-client library."""
```

- **Key operations**:
  - `provision_pvc`: Creates PVC with `ReadWriteMany` access mode, **2Gi** storage. Idempotent (`oc apply`).
  - `provision_pod`: Creates pod from fixed `SANDBOX_IMAGE`, mounts PVC at `/workspace`, applies **pod resource limits** (500m/512Mi request, 2/2Gi limit), `sleep infinity` entrypoint. After pod ready: if `git_token` is provided, clones with `https://{token}@...`; otherwise plain clone. Sets up git worktree.
  - `execute`: `oc.invoke('exec', ...)`.
  - `teardown_pod`: `oc.invoke('delete', ['pod', ..., '--ignore-not-found'])` — idempotent.
  - `is_pod_alive`: Check pod phase is `Running`.
- **Auth context**: Uses `oc.api_server()` / `oc.token()` / `oc.tls_verify()` context manager pattern from `OcExecTool`.
- **Constants**: `SANDBOX_IMAGE`, `PVC_SIZE`, and `POD_RESOURCES` are hardcoded in the adapter — not user-configurable.

---

### 3.7 Temporal Integration — Sandbox Lifecycle in Workflow

#### Modified `BackgroundSessionOps` protocol

`BackgroundSessionOps` is a **Protocol** (structural typing). All implementors **must** implement all methods. There are no default implementations on a Protocol.

```python
@runtime_checkable
class BackgroundSessionOps(Protocol):
    async def begin(self) -> GraphState: ...
    async def execute_graph(self, seeded_state: GraphState) -> GraphState: ...
    async def complete(self, final_state: GraphState) -> None: ...
    async def fail(self, error: Exception) -> None: ...
    async def provision_sandboxes(self) -> None: ...       # NEW
    async def teardown_sandboxes(self) -> None: ...        # NEW
```

Today, only `SessionWorkflow` implements this protocol. Adding two new methods requires updating only that one class. If a future Celery or other adapter implements `BackgroundSessionOps`, it must also implement sandbox methods (which can be no-ops if sandboxes are not supported on that engine).

#### Modified `BackgroundSessionRunner`

```python
class BackgroundSessionRunner:
    async def run(self, ops: BackgroundSessionOps) -> GraphState:
        try:
            seeded_state = await ops.begin()
            await ops.provision_sandboxes()   # NEW
            final_state = await ops.execute_graph(seeded_state)
            await ops.complete(final_state)
            return final_state
        except Exception as e:
            await ops.fail(e)
            raise
        finally:
            await ops.teardown_sandboxes()    # NEW
```

The `finally` block ensures teardown runs even on failure/cancellation. `teardown_sandboxes` must not raise (catch and log errors internally) to avoid masking the original exception.

#### Modified `SessionWorkflowParams`

```python
class SessionWorkflowParams(BaseModel):
    run_id: str
    execution_context: ExecutionContext = Field(default_factory=ExecutionContext)
    graph_execution_params: GraphExecutionParams = Field(default_factory=GraphExecutionParams)
    sandbox_configs: Optional[List[Dict[str, Any]]] = None  # NEW
```

`sandbox_configs` is populated by `TemporalSessionSubmitter` (see §3.8).

#### New Temporal DTO models

```python
class ProvisionSandboxParams(BaseModel):
    run_id: str
    agent_ids: List[str] = Field(default_factory=list)
    sandbox_configs: Optional[List[Dict[str, Any]]] = None

class TeardownSandboxParams(BaseModel):
    run_id: str
    sandbox_state: Optional[SandboxState] = None
    sandbox_configs: Optional[List[Dict[str, Any]]] = None  # cluster auth for teardown
    agent_ids: List[str] = Field(default_factory=list)
```

**Teardown credentials**: `sandbox_configs` is passed in both provision and teardown params. The workflow receives `sandbox_configs` from `SessionWorkflowParams` (set by submitter) and forwards it to both activities. This means teardown always has cluster auth — even when `sandbox_state` is `None` (crash recovery). The config contains `cluster_api`, `cluster_token`, `namespace`, and `skip_tls_verify` — everything needed for `teardown_by_naming` to authenticate and delete pods.

#### Modified `SessionWorkflow` (Temporal)

```python
@workflow.defn
class SessionWorkflow:
    @workflow.run
    async def run(self, params: SessionWorkflowParams) -> GraphState:
        self._params = params
        self._sandbox_state: Optional[SandboxState] = None
        runner = BackgroundSessionRunner()
        return await runner.run(self)

    # ... existing begin, execute_graph, complete, fail ...

    async def provision_sandboxes(self) -> None:
        if not self._params.sandbox_configs:
            return  # no sandbox tools in blueprint — skip
        agent_ids = list(
            self._params.graph_execution_params.graph_definition.nodes.keys()
        )
        self._sandbox_state = await workflow.execute_activity(
            "provision_sandboxes",
            ProvisionSandboxParams(
                run_id=self._params.run_id,
                agent_ids=agent_ids,
                sandbox_configs=self._params.sandbox_configs,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3),
            result_type=SandboxState,
        )

    async def teardown_sandboxes(self) -> None:
        if not self._params.sandbox_configs:
            return  # no sandbox tools — nothing to tear down
        teardown_params = TeardownSandboxParams(
            run_id=self._params.run_id,
            sandbox_state=self._sandbox_state,
            sandbox_configs=self._params.sandbox_configs,   # cluster auth
            agent_ids=list(self._params.graph_execution_params
                          .graph_definition.nodes.keys()),  # from graph
        )
        await workflow.execute_activity(
            "teardown_sandboxes",
            teardown_params,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
```

The `if not sandbox_configs: return` guard ensures workflows without sandbox tools have zero overhead.

#### New `SandboxLifecycleActivities`

```python
class SandboxLifecycleActivities:
    def __init__(
        self,
        sandbox_service: SandboxLifecycleService,
        session_manager: UserSessionManager,
        session_repo: SessionRepository,
    ): ...

    @activity.defn(name="provision_sandboxes")
    def provision(self, params: ProvisionSandboxParams) -> SandboxState:
        """
        1. Load SessionRecord via session_manager.get_record(run_id)
        2. Read record.sandbox_pvc_name (may be set from prior run)
        3. Read agent_ids directly from params.agent_ids
        4. Parse sandbox_configs into SandboxExecToolConfig
        5. Call sandbox_service.provision_for_session(
               run_id, agent_ids, config,
               existing_pvc_name=record.sandbox_pvc_name,
           )
        6. Write record.sandbox_pvc_name = sandbox_state.pvc_name
        7. session_repo.save(record) — persist PVC reference
        8. activity.heartbeat() during pod readiness waits
        9. Return SandboxState
        """

    @activity.defn(name="teardown_sandboxes")
    def teardown(self, params: TeardownSandboxParams) -> None:
        """
        1. Parse config from params.sandbox_configs (cluster auth for oc commands)
        2. If params.sandbox_state exists:
              sandbox_service.teardown_for_session(sandbox_state, config)
           Else (crash recovery — sandbox_state is None):
              sandbox_service.teardown_by_naming(run_id, params.agent_ids, config)
              (config provides cluster_api, token, namespace for auth)
        3. Idempotent — safe to call multiple times
        4. Must not raise — catch and log errors to avoid masking original exception
        """
```

#### Worker Registration

```python
# In worker.py run_worker():
sandbox_activities = SandboxLifecycleActivities(
    sandbox_service=container.sandbox_service,
    session_manager=container.session_manager,
    session_repo=container.session_repo,
)

worker = Worker(
    ...
    activities=[
        graph_activities.execute_node,
        graph_activities.evaluate_condition,
        lifecycle_activities.begin_session,
        lifecycle_activities.complete_session,
        lifecycle_activities.fail_session,
        sandbox_activities.provision,      # NEW
        sandbox_activities.teardown,       # NEW
    ],
    ...
)
```

---

### 3.8 Submitter — Populating `sandbox_configs`

#### Modified `TemporalSessionSubmitter`

```python
class TemporalSessionSubmitter(BackgroundSessionSubmitter):
    async def _start_session_workflow(self, session, request) -> str:
        executor = session.executable_graph
        # ... existing validation ...

        sandbox_configs = self._extract_sandbox_configs(session)

        params = SessionWorkflowParams(
            run_id=session.get_run_id(),
            execution_context=request.execution_context,
            graph_execution_params=graph_params,
            sandbox_configs=sandbox_configs,  # NEW
        )
        # ... start_workflow ...

    def _extract_sandbox_configs(self, session: WorkflowSession) -> Optional[List[Dict]]:
        """
        Scan session_registry for sandbox_exec tool instances.
        Extract their configs as dicts for serialization to Temporal.
        Returns None if no sandbox tools exist.
        """
```

The submitter has access to the full `WorkflowSession` (including `session_registry` with all resolved tools). It scans for `sandbox_exec` type tools and serializes their configs into `sandbox_configs`. If no sandbox tools exist, `sandbox_configs` is `None` and the workflow skips sandbox provisioning entirely.

**Multi-config policy**: If multiple `sandbox_exec` resources exist, each is included in `sandbox_configs`. The `provision_sandboxes` activity uses the **first** config (all configs should point to the same cluster/namespace for a given workflow). A future enhancement could support multi-cluster sandboxes.

---

### 3.9 Session Build — Injecting `SandboxManagerPort` via `ElementDeps`

#### Modified `ElementDeps`

```python
@dataclass
class ElementDeps:
    execution_ctx: Optional[ExecutionContextHolder] = field(default=None)
    auth_service: Optional[AuthService] = field(default=None)
    sandbox_manager: Optional[SandboxManagerPort] = field(default=None)  # NEW
```

No `ToolBuilder._extra_kwargs` override needed. `CategoryBuilder._create_instance` already calls `factory.create(validated, deps=deps, **extra)`, making `deps` available in `kwargs`. The factory reads `deps.sandbox_manager` and `deps.execution_ctx` directly — same pattern as `SlackRetrieverFactory`.

---

### 3.10 Bootstrap — `AppContainer` & `WorkflowSessionFactory` Wiring

`ElementDeps` is constructed inside `WorkflowSessionFactory.build_runtime_plan()`, not in `AppContainer`. The wiring chain is:

#### Modified `WorkflowSessionFactory`

```python
class WorkflowSessionFactory:
    def __init__(
        self,
        element_registry: ElementRegistry,
        engine_name: str,
        auth_service: Optional[AuthService] = None,
        sandbox_manager: Optional[SandboxManagerPort] = None,  # NEW
    ):
        self._elements = element_registry
        self._engine_name = engine_name
        self._auth_service = auth_service
        self._sandbox_manager = sandbox_manager  # NEW

    def build_runtime_plan(
        self,
        blueprint_spec: BlueprintSpec,
        ctx_holder: Optional[ExecutionContextHolder] = None,
    ) -> RTGraphPlan:
        holder = ctx_holder if ctx_holder is not None else ExecutionContextHolder()
        deps = ElementDeps(
            execution_ctx=holder,
            auth_service=self._auth_service,
            sandbox_manager=self._sandbox_manager,  # NEW — threaded through
        )
        logical_plan = PlanBuilder(self._elements).build(blueprint_spec)
        registry = self._session_builder.build(blueprint_spec, deps=deps)
        return RTGraphPlan(logical_plan, registry, self._elements)
```

#### Modified `AppContainer.__init__`

```python
# In AppContainer.__init__:
self.sandbox_manager = OpenShiftSandboxManager()
self.sandbox_service = SandboxLifecycleService(
    sandbox_manager=self.sandbox_manager,
)

# Pass sandbox_manager to factory (factory builds ElementDeps internally):
self.session_factory = WorkflowSessionFactory(
    element_registry=self.element_registry,
    engine_name=cfg.engine_name,
    auth_service=self.auth_service,
    sandbox_manager=self.sandbox_manager,  # NEW
)
```

---

### 3.11 Container Image — `Dockerfile.sandbox`

Hosted by the team at a fixed registry path (`quay.io/<org>/sandbox-base:latest`). **Not user-configurable.**

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash git curl && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash sandbox
WORKDIR /workspace
RUN chown sandbox:sandbox /workspace

USER sandbox
ENTRYPOINT ["sleep", "infinity"]
```

---

## 4. Data Flow

### 4.1 First-Time Workflow Execution

```
User saves sandbox_exec resource (cluster_api, token, namespace, git_repo)
    → resource.save API → MongoResourcesRegistry

User triggers workflow (session.submit)
    → SessionService.submit()
    → TemporalSessionSubmitter.submit():
       - Scans session_registry for sandbox_exec tools
       - Extracts configs into sandbox_configs
       - Builds SessionWorkflowParams(sandbox_configs=[...])
    → client.start_workflow(SessionWorkflow, params)

SessionWorkflow.run():
    1. begin()           → begin_session activity → QUEUED → RUNNING

    2. provision_sandboxes()  → provision_sandboxes activity:
       a. Loads SessionRecord — record.sandbox_pvc_name is None (first run)
       b. Extracts agent_ids from graph_definition node list
       c. Detects and deletes any orphan pods (deterministic names)
       d. SandboxLifecycleService.provision_for_session():
          - Generates pvc_name = "sandbox-pvc-{run_id[:8]}"
          - OpenShiftSandboxManager.provision_pvc() — creates PVC (RWX)
          - For each agent_id:
            - pod_name = "sandbox-{run_id[:8]}-{agent_id}"
            - OpenShiftSandboxManager.provision_pod(git_token=config.git_token)
              - Creates pod (fixed image, 500m/512Mi → 2/2Gi limits), mounts PVC at /workspace
              - Waits for pod Running
              - If no bare repo on PVC: git clone (with token if private) → /workspace/repo.git
              - git worktree add /workspace/worktree-{agent_id} sandbox/{agent_id}
       e. Sets record.sandbox_pvc_name = pvc_name → repo.save(record)
       f. activity.heartbeat() during waits
       g. Returns SandboxState → stored as self._sandbox_state in workflow

    3. execute_graph()   → GraphTraversalWorkflow (child):
       Per node: execute_graph_node activity:
         → GraphNodeActivities passes session_id=params.session_id (per-call, thread-safe)
         → NodeExecutor.execute_node(session_id=params.session_id):
           - Enriches ExecutionContext.tags with run_id and node_uid
           - Sets enriched context on ExecutionContextHolder
           - Builds node from mini-blueprint (tools get holder via deps)
         → CustomAgentNode.run()
           → Agent calls sandbox_exec tool
             → SandboxExecTool.run(cmd="pytest tests/")
               → Reads run_id, node_uid from execution_ctx.context.tags
               → Derives pod_name, workdir from deterministic naming
               → sandbox_manager.execute(pod_name, namespace, ..., cmd)
               ← stdout/stderr returned to agent

    4. complete()        → complete_session activity → COMPLETED

    finally:
    5. teardown_sandboxes() → teardown_sandboxes activity:
       a. Receives self._sandbox_state from workflow
       b. SandboxLifecycleService.teardown_for_session() — deletes all pods
       c. PVC is NOT deleted
```

### 4.2 Re-Trigger (Same Session)

```
User triggers workflow again (same run_id)
    → SessionWorkflow.run():
       provision_sandboxes():
         a. Loads SessionRecord → record.sandbox_pvc_name = "sandbox-pvc-abc12345"
         b. Detects and deletes any orphan pods from prior crashed run
         c. SandboxLifecycleService.provision_for_session(existing_pvc_name=...)
         d. PVC already exists on cluster — provision_pvc() is idempotent
         e. Provisions new pods, mounts existing PVC
         f. Git worktrees already on PVC — checkout existing branches
         g. Returns SandboxState → agents resume with prior filesystem
```

### 4.3 Crash/Cancellation Cleanup

```
Workflow crashes or is cancelled:
    → except Exception → ops.fail(e) → fail_session activity
    → finally → ops.teardown_sandboxes()
       → If self._sandbox_state exists:
            teardown using exact pod names from state
         Else (state never set — crash during provisioning):
            teardown_by_naming — reconstruct pod names from run_id + agent_ids
       → Pods deleted, PVC preserved
       → Errors caught and logged (never raised — avoids masking original error)

If teardown activity itself fails (total system crash):
    → On next re-trigger, provision_sandboxes step (c) detects orphan pods
      (same deterministic names) and deletes before re-provisioning
```

---

## 5. Edge Cases & Risks

### Edge Cases

| Case | Handling |
|------|----------|
| No sandbox_exec tool in blueprint | `sandbox_configs` is `None` → `provision_sandboxes` and `teardown_sandboxes` return immediately (no-op). Zero overhead. |
| Multiple sandbox_exec resources | All configs included in `sandbox_configs`. First config used for provisioning. All must target same cluster/namespace. |
| PVC storage class doesn't support RWX | `provision_pvc` fails fast with clear error. Single-agent workflows fall back to RWO. |
| Pod fails to start (image pull, resource limits) | Temporal retry policy (3 attempts). If all fail, workflow fails. Teardown runs in `finally`. |
| Agent calls sandbox_exec before provisioned | Cannot happen — provisioning completes before `execute_graph`. |
| Same session re-triggered while previous running | `provision_sandboxes` detects existing pods (deterministic names), deletes before re-provisioning. |
| Git clone fails | Surfaced to user via workflow failure. |
| Namespace doesn't exist / lacks permissions | Caught by validator at resource save, and again at provision time. |
| Temporal worker crashes mid-provisioning | Temporal replays. All provision operations are idempotent. |
| Teardown called but sandbox_state is None | Falls back to `teardown_by_naming()` using deterministic pod names. |
| Teardown raises an error | Caught and logged — never propagated to avoid masking the original workflow error. |

### Backward Compatibility

- **`BackgroundSessionOps` Protocol**: Two new required methods. Only `SessionWorkflow` implements this protocol today — single update point. Future adapters must implement them (can be no-ops).
- **`SessionWorkflowParams`**: New optional `sandbox_configs` field (default `None`). Existing serialized params deserialize cleanly.
- **`SessionRecord`**: New `sandbox_pvc_name: Optional[str] = None`. Existing documents deserialize cleanly.
- **`ElementDeps`**: New optional `sandbox_manager` field (default `None`). Existing factories ignore it.
- **`WorkflowSessionFactory`**: New optional `sandbox_manager` parameter (default `None`). Threaded through to `ElementDeps` in `build_runtime_plan()`. Constructor signature change is backward-compatible (keyword-only, default `None`). All callers (`AppContainer`, `worker.py`) must pass it.
- **`ExecutionContext.tags`**: Already `Dict[str, Any]`. Adding `run_id`/`node_uid` keys is additive — existing code that reads tags is unaffected.
- **`NodeExecutor.execute_node`**: New optional `session_id` parameter (default `""`). Constructor unchanged. `GraphNodeActivities` passes `params.session_id` per-call — thread-safe, no shared mutable state.

### Performance Considerations

- Pod provisioning adds ~30-60s to workflow startup. Mitigated by pre-pulling sandbox image.
- PVC provisioning: <5s for most storage classes.
- `oc exec` per tool call: ~100-200ms overhead. Acceptable for code execution.

### Regression Test Matrix

| Area | Test |
|------|------|
| `WorkflowSessionFactory.build_runtime_plan` | Verify `deps` with `sandbox_manager=None` does not break existing tool/retriever builds. |
| `NodeExecutor.execute_node` | Verify `ExecutionContext.tags` enrichment does not break existing node execution (tags were empty dict before). |
| `SessionWorkflow` without sandbox | Verify `sandbox_configs=None` → `provision_sandboxes` is a clean no-op. |
| `SessionRecord` deserialization | Verify existing Mongo documents (without `sandbox_pvc_name`) deserialize as `None`. |
| Graph node execution with shared tool RID | Verify same `sandbox_exec` tool instance works across multiple nodes with different `node_uid` via `ExecutionContext.tags`. |
| `BackgroundSessionRunner` error path | Verify `teardown_sandboxes` in `finally` does not mask the original exception. |

---

## 6. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | **PVC size limit** | Fixed at **2Gi**. Hardcoded in `OpenShiftSandboxManager` (`PVC_SIZE = "2Gi"`). Not user-configurable. |
| 2 | **Pod resource limits** | Hardcoded in `OpenShiftSandboxManager`: requests `cpu: 500m, memory: 512Mi`, limits `cpu: 2, memory: 2Gi`. Not user-configurable. |
| 3 | **Git authentication** | Token-based HTTPS. User provides `git_token` in `SandboxExecToolConfig`. Adapter uses `https://{token}@host/repo` for clone. Empty token = public repo. |
| 4 | **Sandbox image registry** | Fixed image hosted by the team (`quay.io/<org>/sandbox-base:latest`). `container_image` removed from `SandboxExecToolConfig` — hardcoded in the adapter constant `SANDBOX_IMAGE`. |
| 5 | **Foreground session support** | **Only Temporal** (background workflows). `ForegroundSessionRunner` will **not** get sandbox lifecycle hooks. Sandbox is exclusively a background-workflow feature. |

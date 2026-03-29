# ---

**Architecture Design Review (ADR)**

**Feature Name:** Session Cancel — Temporal Workflow Execution Path

**Lead Developer:** Yosi Habushi | **Date:** 2026-03-15 | **Priority:** High

### ---

## 1. Executive Summary

*A high-level view for stakeholders and the Architect.*

| Section | Developer Input |
| :---- | :---- |
| **Problem Statement** | No mechanism exists to stop a running Temporal-backed session. Once a workflow is submitted via `POST /user.session.submit`, it runs to completion regardless of user intent — wasting compute, LLM tokens, and blocking the session in RUNNING state indefinitely if a node hangs. |
| **High-Level Solution** | Add a `POST /session.cancel` endpoint that checks session eligibility (QUEUED/RUNNING), reads the persisted `workflow_id` from the session record, and calls Temporal's `handle.cancel()` via a `BackgroundSessionCanceller` port to stop the workflow. The workflow catches `CancelledError` and runs a `cancel_session` cleanup activity that marks the session as CANCELLED in MongoDB and closes the Redis channel. Lifecycle ownership remains in a single place (the workflow's cleanup activity via `BackgroundLifecycleHandler`). |
| **Success Metrics** | Session status transitions to CANCELLED within seconds of API call (once Temporal delivers `CancelledError` to the workflow and the cleanup activity executes). No new graph nodes start after cancel. Redis stream and active-session tracking cleaned up by the cleanup activity. `complete()`/`fail()` cannot overwrite CANCELLED (terminal state guard). |

### ---

## 2. The "Where": Code & Data Changes

*Identifying the blast radius before coding starts.*

| Area | Details |
| :---- | :---- |
| **Frontend** | No frontend changes in this ADR. This covers the backend Temporal execution path only. Frontend stop button integration is covered by GENIE-1038. |
| **Database** | No new tables or columns. `SessionStatus.CANCELLED` is persisted via the existing `SessionRepository.save()` mechanism. MongoDB documents gain a new possible value `"CANCELLED"` in the `status` field. |
| **Config/Infra** | No new environment variables or third-party keys. Uses existing Temporal client configuration (`temporal_host`, `temporal_namespace`, `temporal_task_queue`) and Redis channel infrastructure. |

### Backend/APIs — File-Level Breakdown

| File | Role | What Changed |
| :---- | :---- | :---- |
| **New File** | | |
| `outbound/temporal/canceller.py` | Outbound adapter | New `TemporalSessionCanceller`. Calls `handle.cancel()`. Bridges sync Flask / async Temporal via `asyncio.run()`. |
| **Domain Layer (lib/mas/)** | | |
| `session/service.py` | App service | Added `cancel()` — checks eligibility, reads `workflow_id` from tags, delegates to canceller. Modified `submit()` to persist `workflow_id` in tags. Added `background_canceller` to constructor. |
| `session/execution/ports.py` | Port (interface) | Added `BackgroundSessionCanceller` abstract class with `cancel(session_id, workflow_id)`. Domain contract — doesn't know it's Temporal. |
| `session/execution/__init__.py` | Package exports | Export `BackgroundSessionCanceller`. |
| `session/execution/lifecycle.py` | State machine | Added `cancel(record)` — sets CANCELLED + `finished_at`. Added guards in `complete()`/`fail()` to no-op if already CANCELLED. |
| `session/execution/lifecycle_handler.py` | Lifecycle handler | Added `cancel(run_id)` — fetches record, calls `lifecycle.cancel()`, then `_close_channel()`. Same pattern as `complete()`/`fail()`. |
| `session/domain/status.py` | Status enum | Added `CANCELLED` to `SessionStatus`. |
| `session/management/user_session_manager.py` | Data access | Supporting changes for cancel flow. |
| **Temporal Shared Layer** | | |
| `temporal/models.py` | DTO | Added `CancelSessionParams(run_id: str)` — data object sent to `cancel_session` activity. |
| **Temporal Inbound Adapters** | | |
| `temporal/workflows/session_workflow.py` | Workflow | Added `try/except CancelledError` in `run()`. Executes `cancel_session` cleanup activity, then re-raises. |
| `temporal/activities/session_lifecycle_activities.py` | Activity | Added `cancel_session` activity — one-liner delegates to `handler.cancel(run_id)`. |
| `temporal/worker.py` | Worker reg. | Registered `cancel_session` activity. |
| **API Layer** | | |
| `flask/endpoints/sessions.py` | Flask endpoint | Added `POST /session.cancel`. Returns 200 or 409. |
| **Bootstrap** | | |
| `bootstrap/container.py` | DI wiring | Wire `TemporalSessionCanceller` into `SessionService`. |

### ---

## 3. Architecture & AI Strategy

*The "logic" of the solution.*

| Component | Design Details |
| :---- | :---- |
| **System Diagram** | See diagrams below. |
| **LLM / Model** | Not applicable — this feature operates at the graph orchestration layer. It cancels the Temporal workflow that dispatches node activities, not the LLM provider call itself. The currently-executing LLM call (if any) completes naturally; no new nodes are dispatched after cancellation. |
| **Context Strategy** | Not applicable — this feature does not modify prompt construction or context assembly. |
| **Output Validation** | On cancellation, the session's `GraphState` is preserved at the last successfully completed superstep. The session record retains all state accumulated before cancellation. Subscribers see the stream close (via `__control: close`), cleanly ending the connection. The session status in MongoDB distinguishes cancellation from normal completion or failure. |

### Diagram 1 — Execution Stages: Full Journey of a User Query

Every query passes through 6 stages from submission to answer. Each stage is a potential cancel interception point.

```
STAGE 1: API LAYER (Flask)
──────────────────────────────────────────────────────────────────
  POST /user.session.submit
    { sessionId: "abc123", inputs: { query: "What is K8s?" } }

  SessionService.submit(session_id, inputs)
    |-- _stage(): project inputs onto SessionRecord, save to MongoDB
    |             status: PENDING -> QUEUED
    +-- _submitter.submit(): start Temporal workflow
    |     +-- generate workflow_id = "session-{runId}-{uuid4().hex[:8]}"
    |     +-- client.start_workflow(id=workflow_id)
    +-- save workflow_id to record.run_context.tags["workflow_id"]
          (persisted to MongoDB — used later by cancel to find the workflow)

  Response: 202 { sessionId: "abc123", workflowId: "session-abc123-7f3a9b1e" }


STAGE 2: TEMPORAL TASK QUEUE
──────────────────────────────────────────────────────────────────
  The workflow task sits in Temporal's task queue waiting for
  a worker to pick it up.

  +---------------------------------------------+
  |  Task Queue: "graph-engine"                  |
  |  +---------------------------------------+   |
  |  | SessionWorkflow (session-abc123)      |   |  <-- waiting
  |  +---------------------------------------+   |
  +---------------------------------------------+


STAGE 3: BEGIN SESSION (Temporal Activity)
──────────────────────────────────────────────────────────────────
  SessionWorkflow.run() -> BackgroundSessionRunner.run(self)
    +-- self.begin()
          +-- begin_session activity
                +-- BackgroundLifecycleHandler.begin()
                      |-- get record from MongoDB
                      |-- status: QUEUED -> RUNNING
                      |-- bind run context
                      +-- save to MongoDB

  Returns: seeded GraphState (with user inputs)


STAGE 4: GRAPH TRAVERSAL (Child Workflow)
──────────────────────────────────────────────────────────────────
  SessionWorkflow.execute_graph(seeded_state)
    +-- starts GraphTraversalWorkflow as child workflow
          +-- GraphTraversal.run() -- BSP superstep loop

  +-----------------------------------------------------------+
  |                    BSP SUPERSTEP LOOP                       |
  |                                                            |
  |  For each superstep:                                       |
  |                                                            |
  |  +----------+    +----------+    +----------+              |
  |  |   PLAN   |--->| EXECUTE  |--->|  UPDATE  |---> next     |
  |  |          |    |          |    |          |              |
  |  | Which    |    | Run node |    | Merge    |              |
  |  | nodes    |    | activit- |    | results  |              |
  |  | are      |    | ies in   |    | into     |              |
  |  | ready?   |    | parallel |    | state    |              |
  |  +----------+    +----------+    +----------+              |
  |       ^                                |                   |
  |       +--------------------------------+                   |
  |                  (repeat until no active nodes)            |
  +-----------------------------------------------------------+

  EXAMPLE GRAPH WITH 3 NODES:
    Superstep 0: [planner_node]   <-- activity dispatched to worker
    Superstep 1: [llm_agent_node] <-- activity dispatched to worker
    Superstep 2: [summary_node]   <-- activity dispatched to worker
    No more active nodes -> loop ends


STAGE 5: NODE EXECUTION (Temporal Activity -- per node)
──────────────────────────────────────────────────────────────────
  5a. Activity task placed in Temporal task queue
      +---------------------------------------------+
      |  Task Queue: "graph-engine"                  |
      |  +---------------------------------------+   |
      |  | execute_graph_node (node: "llm_agent")|   |  <-- waiting
      |  +---------------------------------------+   |
      +---------------------------------------------+

  5b. Worker picks up activity, executes node
      NodeExecutor.execute_node()
        |-- rebuild node from mini-blueprint
        |-- inject StepContext
        |-- inject SessionChannel (for streaming)
        +-- step.func(state, config={})  <-- THE ACTUAL WORK
              |-- e.g. LLM API call (5-30 seconds)
              |-- e.g. MCP tool call (2-5 seconds)
              +-- e.g. data transform (< 1 second)

  5c. During execution, node emits streaming events
      channel.emit({"type": "agent_message", "content": "..."})
        +-- Redis XADD -> mas:stream:abc123
              +-- subscriber reads via XREAD
                    +-- client sees live tokens

  5d. Activity returns updated GraphState
      -> back to Stage 4 (UPDATE phase, then next superstep)



STAGE 6: COMPLETE SESSION (Temporal Activity)
──────────────────────────────────────────────────────────────────
  BackgroundSessionRunner calls ops.complete(final_state)
    +-- complete_session activity
          +-- BackgroundLifecycleHandler.complete()
                |-- attach final GraphState to record
                |-- status: RUNNING -> COMPLETED
                |-- save to MongoDB
                +-- close Redis channel
                      |-- XADD {__control: "close"}
                      |-- remove from active sessions set
                      +-- delete Redis stream

  Subscriber sees CLOSE signal -> stops reading
```

### Diagram 2 — Hexagonal Architecture Layers (Cancel Flow)

The cancel flow passes through the architecture layers twice: once to send the signal, once to handle the cleanup.

```
PHASE A: SEND THE CANCEL SIGNAL
(User → Flask → Domain → Temporal)
══════════════════════════════════════════════════════════════════

Step 1 │ INBOUND         │ Flask receives POST /session.cancel
       │                  │ Extracts session_id = "abc123"
       │                  │
       ▼                  │
Step 2 │ DOMAIN           │ SessionService.cancel("abc123")
       │                  │   1. Fetch record from MongoDB
       │                  │   2. Guard: status is QUEUED or RUNNING?
       │                  │      NO → return 409  |  YES → continue
       │                  │   3. Read workflow_id from record tags
       │                  │   4. Call canceller.cancel(session_id, workflow_id)
       │                  │      (calls the PORT — doesn't know it's Temporal)
       │                  │
       │                  │   NOTE: No DB write here. Domain only SIGNALS.
       ▼                  │
Step 3 │ OUTBOUND         │ TemporalSessionCanceller.cancel()
       │                  │   handle = client.get_workflow_handle(workflow_id)
       │                  │   handle.cancel()  → sends cancel to Temporal
       │                  │   (catches exceptions if workflow already done)
       │                  │
       ▼                  │
Step 4 │                  │ Flask returns 200 { status: "CANCELLED" }
       │                  │ (or 409 if not cancellable)


══════════════════════════════════════════════════════════════════
  ... Temporal delivers CancelledError to the workflow ...
══════════════════════════════════════════════════════════════════


PHASE B: HANDLE THE CLEANUP
(Temporal → Worker → Domain → MongoDB + Redis)
══════════════════════════════════════════════════════════════════

Step 5 │ INBOUND         │ SessionWorkflow catches CancelledError
       │                  │ Runs cancel_session activity on worker
       │                  │
       ▼                  │
Step 6 │ DOMAIN           │ BackgroundLifecycleHandler.cancel(run_id)
       │                  │   1. lifecycle.cancel(record)
       │                  │      → status = CANCELLED, save to MongoDB
       │                  │   2. _close_channel(run_id)
       │                  │      → XADD {__control: close}
       │                  │      → SREM from active set
       │                  │      → DELETE stream
       │                  │
       ▼                  │
Step 7 │                  │ Workflow re-raises CancelledError
       │                  │ Temporal marks workflow as cancelled
       │                  │ Subscriber sees close signal, stops reading


══════════════════════════════════════════════════════════════════
  GUARDS: complete()/fail() no-op if status is already CANCELLED
══════════════════════════════════════════════════════════════════
```

### Diagram 3 — Cancel Sequence (Full Data Flow)

```
CLIENT                     FLASK API                   TEMPORAL                    WORKER
  │                            │                          │                          │
  │ POST /session.cancel       │                          │     (running graph)      │
  │───────────────────────────>│                          │                          │
  │                            │                          │                          │
  │                            │ 1. SessionService        │                          │
  │                            │    .cancel(session_id)   │                          │
  │                            │                          │                          │
  │                            │ 2. Check status guard    │                          │
  │                            │    (must be QUEUED or    │                          │
  │                            │     RUNNING)             │                          │
  │                            │                          │                          │
  │                            │ 3. Read workflow_id from │                          │
  │                            │    record.run_context    │                          │
  │                            │    .tags["workflow_id"]  │                          │
  │                            │                          │                          │
  │                            │ 4. TemporalSession-      │                          │
  │                            │    Canceller.cancel()    │                          │
  │                            │    │                     │                          │
  │                            │    │── handle.cancel() ─>│                          │
  │                            │                          │                          │
  │  200 {status: CANCELLED}   │                          │ CancelledError raised    │
  │<───────────────────────────│                          │ at next await point      │
  │                            │                          │                          │
  │                            │                          │ SessionWorkflow catches  │
  │                            │                          │   CancelledError         │
  │                            │                          │                          │
  │                            │                          │ cancel_session activity  │
  │                            │                          │────────── runs ─────────>│
  │                            │                          │   handler.cancel(run_id) │
  │                            │                          │     lifecycle.cancel()   │
  │                            │                          │       RUNNING → CANCELLED│
  │                            │                          │       (DB write)         │
  │                            │                          │     _close_channel()     │
  │  {__control: close}        │                          │       channel.close()    │
  │<~~~~ subscriber stops ~~~~~│~~~~~~~~~~~~~~~~~~~~~~~~~~│~~~~~~~~~~~~~~~~~~~~~~~~~>│
```

### Diagram 4 — Stage-by-Stage Cancellation Behavior

```
STAGE                        WHAT HAPPENS
───────────────────────────────────────────────────────────────────────────
1. QUEUED in Temporal        handle.cancel() cancels before workflow starts.
   (workflow not started)    Cleanup activity marks CANCELLED + closes channel.

2. begin_session activity    Activity is short (~200ms). Temporal delivers
   (marking RUNNING)         CancelledError after it finishes. complete/fail
                             guards prevent overwriting.

3. Between supersteps        CancelledError raised at next await. No new
   (BSP PLAN phase)          nodes dispatched. Cleanup activity runs.

4. Node activity executing   Current node finishes in background (LLM call
   (e.g. LLM API call)      completes naturally). CancelledError at next
                             await after activity returns. Cleanup activity
                             marks CANCELLED + closes channel. No new
                             nodes dispatched.

5. complete/fail activity    Guards check: status is CANCELLED, so
   (final lifecycle)         complete/fail become no-ops.
```

### Diagram 5 — Temporal Workflow Hierarchy and Cancel Propagation

```
┌──────────────────────────────────────────────────────────────────┐
│  TEMPORAL CLUSTER                                                │
│                                                                  │
│  handle.cancel()                                                 │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────┐                        │
│  │ SessionWorkflow                     │                        │
│  │ id: session-{run_id}-{uuid[:8]}     │                        │
│  │                                     │                        │
│  │  try:                               │                        │
│  │    runner.run(self)                  │                        │
│  │  except CancelledError:  ◀── raised │                        │
│  │    execute_activity(     ◀── cleanup│                        │
│  │      "cancel_session")              │                        │
│  │                                     │                        │
│  │  ┌───────────────────────────────┐  │                        │
│  │  │ GraphTraversalWorkflow        │  │  CANCEL PROPAGATES     │
│  │  │ id: session-{run_id}-graph    │  │  AUTOMATICALLY FROM    │
│  │  │                               │  │  PARENT TO CHILD       │
│  │  │  BSP Loop:                    │  │                        │
│  │  │    await execute_node(...)    │◀─┼── CancelledError here  │
│  │  │    await evaluate_condition() │  │                        │
│  │  └───────────────────────────────┘  │                        │
│  └─────────────────────────────────────┘                        │
│                                                                  │
│  OTHER WORKFLOWS: UNAFFECTED                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐               │
│  │ session-xyz789       │  │ session-def456       │              │
│  │ (still running)      │  │ (still running)      │              │
│  └─────────────────────┘  └─────────────────────┘               │
│                                                                  │
│  WORKERS: ALL STAY ALIVE AND HEALTHY                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │                       │
│  └──────────┘  └──────────┘  └──────────┘                       │
└──────────────────────────────────────────────────────────────────┘
```

### Diagram 6 — Redis Channel Cancellation Deep Dive

The cancel mechanism reuses the existing `close()` method — zero new Redis logic. The cleanup activity on the worker calls `_close_channel()`, the same method used by `complete()` and `fail()`.

#### What the Redis Stream Looks Like During a Running Session

```
REDIS SERVER
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Key: "mas:stream:abc123"  (a Redis Stream)                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ msg-1  { payload: '{"type":"agent_message",...}' }     │  │
│  │ msg-2  { payload: '{"type":"agent_message",...}' }     │  │
│  │ msg-3  { payload: '{"type":"tool_call",...}' }         │  │
│  │ ...more events arriving as node executes...             │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Key: "mas:sessions:active"  (a Redis Set)                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  { "abc123", "xyz789", "def456" }                      │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

#### What Happens on Cancel (BackgroundLifecycleHandler in the Worker)

The `TemporalSessionCanceller` (outbound adapter) only sends `handle.cancel()` to Temporal. The actual Redis cleanup is performed by `BackgroundLifecycleHandler.cancel()`, which runs as the `cancel_session` activity inside the workflow's `CancelledError` handler on the worker side.

```
BackgroundLifecycleHandler.cancel(run_id):
─────────────────────────────────────────────────────
  STEP 1: lifecycle.cancel(record)
    ├─ record.status = CANCELLED
    ├─ record.run_context = mark_finished() (sets finished_at)
    └─ repo.save(record)
       → MongoDB write: { status: "CANCELLED", finished_at: now }

  STEP 2: _close_channel(run_id)   →   channel.close()
    (THREE Redis commands — same as complete/fail paths)

    2a. redis.XADD("mas:stream:abc123", {__control: "close"})

        Stream after:
        ┌─────────────────────────────────────────────────────┐
        │ msg-1  { payload: '{"type":"agent_message",...}' }  │
        │ msg-2  { payload: '{"type":"agent_message",...}' }  │
        │ msg-3  { payload: '{"type":"tool_call",...}' }      │
        │ msg-4  { __control: "close" }                       │  <-- CONTROL
        └─────────────────────────────────────────────────────┘

    2b. redis.SREM("mas:sessions:active", "abc123")
        Active set: { "xyz789", "def456" }  (abc123 removed)

    2c. redis.DELETE("mas:stream:abc123")
        Stream deleted from Redis.
```

#### What the Reader Sees (Existing Code, No Changes)

```
Reader's XREAD returns batch with msg-4:

  msg-4: { __control: "close" }
         -> has CONTROL field
         -> return                                   <- iterator STOPS
         -> Flask generator ends
         -> HTTP response stream closes

The client distinguishes cancellation from completion by checking the
session status via the API (GET /session.status) — the status will be
CANCELLED rather than COMPLETED or FAILED.
```

### ---

## 4. Risk & Reliability (AI-Era Checklist)

*Addressing the non-deterministic nature of AI.*

| Risk | Mitigation Plan |
| :---- | :---- |
| **LLM Failure** | Not directly applicable. However, the cancellation mechanism serves as a safety valve when an LLM call hangs — users can stop execution rather than waiting for the 15-minute activity timeout. The current node completes naturally; cancellation takes effect at the next await boundary. |
| **Data Privacy** | No change — cancellation does not introduce new data flows. Partial `GraphState` from completed supersteps is identical to what would be accumulated during a complete run. No additional data is exposed or persisted. |
| **Cost Control** | This feature **reduces** cost by allowing users to stop unnecessary LLM invocations early. In a multi-node graph with 5-10 remaining nodes, each consuming 2K-10K tokens, a timely cancel can save 10K-100K tokens per stopped execution. |
| **Performance** | The cancel API call is lightweight: one MongoDB read (`get_record` for status guard + workflow_id lookup) + one Temporal RPC (`handle.cancel`). Total latency < 100ms. The DB write (`lifecycle.cancel`) and Redis cleanup (`channel.close`) happen asynchronously in the workflow's cleanup activity on the worker. The status guard check in `complete()`/`fail()` adds a single enum comparison (nanoseconds). Temporal's cancel propagation to child workflows is immediate. No polling loops or background threads introduced. |

### ---

## 5. Key Design Decisions & Rationale

*Trade-offs, idempotency guarantees, and failure-mode analysis.*

### 5.1 — `CancelledError` Propagation Through `BackgroundSessionRunner`

The existing `BackgroundSessionRunner.run()` catches `Exception` and calls `ops.fail(e)`. Since Python 3.9, `asyncio.CancelledError` inherits from `BaseException`, **not** `Exception`. This means the runner's error handler does not intercept cancellation — the `CancelledError` propagates directly to `SessionWorkflow.run()` where the Temporal-specific cleanup logic lives. The runner's `ops.fail()` is never called during cancellation, which is the intended behavior: cancellation is not a failure.

This property is essential to the design. It means the domain-level `BackgroundSessionRunner` remains unmodified — cancellation is handled entirely in the Temporal adapter layer where it belongs.

### 5.2 — Single-Owner Lifecycle Transition

The cancel design deliberately avoids performing lifecycle transitions (DB write) or channel cleanup (Redis close) in the API path. Both happen exclusively in the workflow's `CancelledError` handler via `BackgroundLifecycleHandler.cancel()`. This keeps lifecycle ownership in a single place — the same pattern used by `complete()` and `fail()`, which also run as Temporal activities on the worker side.

The API path only: (1) guards on status eligibility, (2) reads the persisted `workflow_id`, and (3) sends the Temporal cancel RPC. The actual state mutation is deferred to the worker.

### 5.3 — Temporal `handle.cancel()` Failure Resilience

If `handle.cancel()` fails (Temporal cluster unavailable, workflow already completed), the `TemporalSessionCanceller` catches and suppresses the exception with a warning log, preventing a Temporal outage from blocking the cancel API response. The API still returns `200` to the client.

In this failure scenario, the workflow continues running to natural completion. The `complete()`/`fail()` lifecycle guards in `SessionLifecycle` do **not** need to check for CANCELLED status because the status was never changed — the cancel simply did not take effect. The session completes normally.

If the user retries the cancel and Temporal is available, the cancel will succeed normally.

### 5.4 — Cleanup Activity as the Primary Cancel Mechanism

In the Temporal Python SDK, workflows can execute cleanup activities inside a `CancelledError` handler before the workflow is marked cancelled. If the cleanup activity itself fails or times out, the original `CancelledError` is re-raised and the workflow is marked cancelled regardless.

The `cancel_session` cleanup activity is the **primary** cancel mechanism (not a safety net). It is responsible for:

- Transitioning the session status to CANCELLED via `SessionLifecycle.cancel()`
- Closing the Redis channel via `_close_channel()`

This also handles direct Temporal admin cancellation (bypassing the API), since the cleanup activity runs regardless of how the workflow was cancelled.

### 5.5 — Lightweight Record Fetch for Cancel + Workflow ID Persistence

`SessionService.cancel()` uses `manager.get_record(session_id)` (lightweight DB fetch) rather than `manager.get_session(session_id)` (expensive full graph hydration with blueprint resolution and node compilation). Cancellation only needs the session's status and `run_context.tags["workflow_id"]` — not the executable graph. This follows the same pattern used by `get_status()`, `get_state()`, and `BackgroundLifecycleHandler`.

The workflow ID is persisted by `SessionService.submit()` into `record.run_context.tags["workflow_id"]` using the existing `update_context(tags=...)` + `save_record()` pattern — the same mechanism that `SessionLifecycle.begin()` uses for scope. This avoids introducing any new persistence mechanism and keeps the workflow ID available for cancellation without requiring deterministic IDs (which would break the "continue conversation" scenario where multiple workflows map to the same session).

### ---

## 6. Reviewer's Feedback

| Status | Feedback / Required Changes |
| :---- | :---- |
| **[ ] Approved** | |
| **[ ] Revise** | |

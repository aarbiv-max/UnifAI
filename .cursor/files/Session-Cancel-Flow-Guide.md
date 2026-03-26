# Session Cancel — Complete Flow Guide

## Part 1: The Normal Workflow (No Cancel)

Before understanding cancel, you need to know how a normal session runs. Here are the 6 stages:

```
User types a question
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 1: API                                           │
│  Flask receives POST /user.session.submit               │
│  SessionService.submit() saves inputs to MongoDB        │
│  Status: PENDING → QUEUED                               │
│  Starts a Temporal workflow                             │
│  Returns 202 immediately (non-blocking)                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 2: QUEUE                                         │
│  The workflow task sits in Temporal's queue              │
│  Waiting for a worker to pick it up                     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 3: BEGIN                                         │
│  Worker picks up the workflow                           │
│  begin_session activity runs                            │
│  Status: QUEUED → RUNNING                               │
│  Returns the GraphState with user inputs                │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 4: GRAPH TRAVERSAL                               │
│  Child workflow runs the BSP superstep loop:            │
│                                                         │
│    PLAN → which nodes are ready?                        │
│    EXECUTE → run those nodes (LLM calls, tools, etc.)   │
│    UPDATE → merge results into state                    │
│    REPEAT until no more active nodes                    │
│                                                         │
│  Each node runs as a separate Temporal activity.        │
│  Nodes stream live tokens to Redis for the frontend.    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 5: NODE EXECUTION (inside each superstep)        │
│  Worker runs the node's function:                       │
│    - LLM API call (5-30 seconds)                        │
│    - MCP tool call (2-5 seconds)                        │
│    - Data transform (< 1 second)                        │
│  Streams events to Redis → frontend sees live tokens    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 6: COMPLETE                                      │
│  complete_session activity runs                         │
│  Status: RUNNING → COMPLETED                            │
│  Saves final state to MongoDB                           │
│  Closes Redis channel (close signal + cleanup)          │
│  Frontend sees stream close → shows final answer        │
└─────────────────────────────────────────────────────────┘
```

---

## Part 2: Where Can Cancel Interrupt?

The user can click "Stop" at **any time** during stages 1-5. Here's what happens at each checkpoint:

```
CHECKPOINT               │ WHAT HAPPENS WHEN USER CLICKS STOP
═════════════════════════╪═══════════════════════════════════════════════════
                         │
Stage 1-2: QUEUED        │ Workflow hasn't started yet.
(in the queue)           │ Temporal cancels it before it runs.
                         │ Cleanup activity marks CANCELLED.
                         │
─────────────────────────┼───────────────────────────────────────────────────
                         │
Stage 3: BEGIN           │ begin_session activity is running (~200ms).
(marking RUNNING)        │ It finishes naturally (too fast to interrupt).
                         │ CancelledError raised right after.
                         │ Cleanup activity marks CANCELLED.
                         │ Guards prevent complete()/fail() from
                         │ overwriting.
                         │
─────────────────────────┼───────────────────────────────────────────────────
                         │
Stage 4: BETWEEN         │ The workflow is awaiting the next superstep.
SUPERSTEPS               │ CancelledError raised immediately.
                         │ No new nodes are dispatched.
                         │ Cleanup activity marks CANCELLED.
                         │
─────────────────────────┼───────────────────────────────────────────────────
                         │
Stage 5: NODE RUNNING    │ A node is mid-execution (e.g. LLM API call).
(LLM call in progress)   │ The current call FINISHES NATURALLY.
                         │   (you don't kill a call mid-stream)
                         │ After it returns, CancelledError raised.
                         │ No NEW nodes are dispatched.
                         │ Cleanup activity marks CANCELLED.
                         │
─────────────────────────┼───────────────────────────────────────────────────
                         │
Stage 6: COMPLETING      │ Too late — session already finished.
                         │ Cancel API returns 409 (not cancellable).
                         │ Session shows as COMPLETED normally.
                         │
═════════════════════════╪═══════════════════════════════════════════════════
```

**Key insight:** The cancel never kills anything mid-execution. It waits for the current work to finish, then prevents anything new from starting.

---

## Part 3: The Cancel Flow Step by Step

When the user clicks Stop, two things happen in sequence:

### Phase A: Send the signal (fast — under 100ms)

```
Step 1  USER clicks Stop button
          │
Step 2  FRONTEND calls POST /session.cancel
          │
Step 3  BACKEND (Flask endpoint)
          │  SessionService.cancel(session_id)
          │    → fetch record from MongoDB (lightweight)
          │    → check: is status QUEUED or RUNNING?
          │       NO → return 409 (can't cancel)
          │       YES → read workflow_id from record tags
          │    → call canceller.cancel(session_id, workflow_id)
          │
Step 4  TEMPORAL CANCELLER (outbound adapter)
          │  handle = client.get_workflow_handle(workflow_id)
          │  handle.cancel()  →  fire-and-forget signal to Temporal
          │
Step 5  FRONTEND receives 200, immediately:
          → Stops the stream reader (cancelStream)
          → Hides typing indicator
          → Shows "Session was stopped by user."
          → Swaps Stop button back to Send button
```

### Phase B: Cleanup (happens on the worker, seconds later)

```
Step 6  TEMPORAL delivers CancelledError to the workflow
          at whatever await point it's currently on
          │
Step 7  SessionWorkflow catches CancelledError
          │  Runs cancel_session activity:
          │    → BackgroundLifecycleHandler.cancel(run_id)
          │      → lifecycle.cancel(record)
          │         status → CANCELLED in MongoDB
          │      → channel.close()
          │         → XADD {__control: close} to Redis stream
          │         → SREM from active sessions set
          │         → DELETE stream key
          │
Step 8  Workflow re-raises CancelledError
          → Temporal marks workflow as cancelled
          → Done
```

---

## Part 4: How It Fits the Hexagonal Architecture

The codebase follows hexagonal architecture, which means:

- **Domain** (center) = business logic. Doesn't know about Flask, Temporal, or Redis.
- **Adapters** (edges) = connect the domain to the real world.
- **Ports** (interfaces) = contracts the domain defines. Adapters implement them.

### The pattern every feature follows

```
INBOUND ADAPTER → calls → DOMAIN → calls → PORT → implemented by → OUTBOUND ADAPTER
(Flask, Temporal)         (service,         (interface)              (MongoDB, Redis,
                           lifecycle)                                 Temporal client)
```

### How cancel follows this pattern

**Sending the cancel signal:**

```
Flask endpoint                → SessionService.cancel()    → BackgroundSessionCanceller.cancel()
(inbound adapter)               (domain — makes decisions)    (port — abstract interface)
                                                                        │
                                                               implemented by
                                                                        │
                                                              TemporalSessionCanceller
                                                              (outbound adapter — calls
                                                               Temporal's handle.cancel())
```

**Handling the cleanup:**

```
SessionWorkflow               → cancel_session activity    → BackgroundLifecycleHandler.cancel()
(inbound adapter —               (thin wrapper)               (domain — does the work)
 catches CancelledError)                                       │
                                                               ├→ SessionLifecycle.cancel()
                                                               │   (domain — status change)
                                                               │
                                                               └→ _close_channel()
                                                                   → RedisSessionChannel.close()
                                                                     (outbound adapter — Redis)
```

### Why this matters

The `SessionService` (domain) calls `self._canceller.cancel()` — it has no idea it's calling Temporal. If you replaced Temporal with Celery, you'd create a `CelerySessionCanceller` that implements the same `BackgroundSessionCanceller` port, and the domain wouldn't change at all.

Same for the cleanup: `BackgroundLifecycleHandler.cancel()` doesn't know it was triggered by a Temporal activity. It just does its job (update DB, close channel). The same handler works for any background execution engine.

---

## Part 5: Codebase Patterns This Feature Reuses

The cancel feature doesn't invent new patterns. It copies existing ones:

### Pattern 1: Lifecycle Transitions

`begin()`, `complete()`, and `fail()` already existed in `SessionLifecycle`. The cancel feature adds `cancel()` following the exact same shape:

```
EXISTING                              NEW (CANCEL)
──────────────────────────────────    ──────────────────────────────────
lifecycle.begin(record, scope)        lifecycle.cancel(record)
  record.status = RUNNING               record.status = CANCELLED
  repo.save(record)                      repo.save(record)

lifecycle.complete(record, state)     Guards added to existing methods:
  record.status = COMPLETED             if record.status == CANCELLED:
  repo.save(record)                       return  (no-op)

lifecycle.fail(record, error)
  record.status = FAILED
  repo.save(record)
```

### Pattern 2: Background Lifecycle Handler

`complete()` and `fail()` already existed in `BackgroundLifecycleHandler`. Cancel adds `cancel()` with the same structure:

```
EXISTING                              NEW (CANCEL)
──────────────────────────────────    ──────────────────────────────────
handler.complete(run_id, state)       handler.cancel(run_id)
  record = manager.get_record()         record = manager.get_record()
  lifecycle.complete(record, state)     lifecycle.cancel(record)
  _close_channel(run_id)               _close_channel(run_id)

handler.fail(run_id, error_msg)
  record = manager.get_record()
  lifecycle.fail(record, error)
  _close_channel(run_id)
```

Notice: `cancel()` calls the same `_close_channel()` as `complete()` and `fail()`. Zero new Redis logic.

### Pattern 3: Temporal Activities as Thin Wrappers

Every lifecycle activity is a one-liner that delegates to the handler:

```
EXISTING                              NEW (CANCEL)
──────────────────────────────────    ──────────────────────────────────
@activity.defn(name="begin_session")  @activity.defn(name="cancel_session")
def begin_session(params):            def cancel_session(params):
  return handler.begin(...)             handler.cancel(params.run_id)

@activity.defn(name="complete_session")
def complete_session(params):
  handler.complete(...)

@activity.defn(name="fail_session")
def fail_session(params):
  handler.fail(...)
```

### Pattern 4: Outbound Adapter with asyncio.run()

The canceller uses the same sync-to-async bridge as the submitter:

```
EXISTING (submitter)                  NEW (canceller)
──────────────────────────────────    ──────────────────────────────────
class TemporalSessionSubmitter:       class TemporalSessionCanceller:

  def submit(self, ...):                def cancel(self, ...):
    asyncio.run(                          asyncio.run(
      self._start_workflow(...)             self._cancel_workflow(...)
    )                                     )

  async def _start_workflow(...):       async def _cancel_workflow(...):
    client = await get_client()           client = await get_client()
    await client.start_workflow()         handle = client.get_handle()
                                          await handle.cancel()
```

### Pattern 5: Port (Abstract Interface)

The submitter port already existed. The canceller port follows the same pattern:

```
EXISTING (submitter)                  NEW (canceller)
──────────────────────────────────    ──────────────────────────────────
class BackgroundSessionSubmitter:     class BackgroundSessionCanceller:
  @abstractmethod                       @abstractmethod
  def submit(self, session,             def cancel(self, session_id,
             request) -> str: ...                  workflow_id) -> None: ...
```

### Pattern 6: UI — Button Swap

The frontend uses the same pattern as ChatGPT/Claude: the Send button and Stop button occupy the same position and swap based on state:

```
IS STREAMING?     BUTTON SHOWN
──────────────    ──────────────
YES               Stop (red, Square icon)
NO                Send (primary, Send icon)
```

This uses the existing `shadcn Button` component, `lucide-react` icons, and the existing `isTyping`/`isLiveRequest` state variables.

---

## Part 6: The Status State Machine

Here's the complete lifecycle of a session status:

```
                    PENDING
                       │
                   submit()
                       │
                    QUEUED
                       │
                   begin()
                       │
                    RUNNING
                   /   |   \
              cancel  complete  fail
                /      |        \
          CANCELLED  COMPLETED  FAILED
           (terminal)  (terminal)  (terminal)

Rules:
  - CANCELLED, COMPLETED, FAILED are all terminal (final) states
  - Once CANCELLED, complete() and fail() become no-ops (guards)
  - Once COMPLETED or FAILED, cancel returns 409 (not cancellable)
  - CANCELLED can only happen from QUEUED or RUNNING
```

---

## Summary

| Question | Answer |
| :---- | :---- |
| What does the cancel do? | Sends a signal to Temporal, which stops the workflow after the current activity finishes. |
| Does it kill an LLM call mid-execution? | No. The current call finishes. No new calls start. |
| Where does the DB write happen? | In the workflow's cleanup activity (worker side), not in the API. |
| Why not write CANCELLED in the API? | Single-owner principle — only the workflow changes lifecycle status, same as complete/fail. |
| What pattern does cancel follow? | Same as complete/fail: activity → handler → lifecycle → repo.save(). |
| Does it need new Redis logic? | No. Reuses the existing channel.close() method. |
| What architecture layer handles what? | Inbound adapters trigger it, domain decides and executes, outbound adapters talk to Temporal/Redis. |
| Is any new pattern introduced? | No. Every piece copies an existing pattern in the codebase. |

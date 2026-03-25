# Session Cancel — Simple Explanation

## The Big Picture (One Sentence)

When a user clicks "Stop", the API tells Temporal to cancel the workflow, the workflow catches that cancellation, runs a cleanup activity that marks the session as CANCELLED in the database and closes the streaming channel. Done.

---

## Step 1: User Clicks "Stop" (API Layer)

**What happens:** The frontend sends `POST /session.cancel` with the `sessionId`.

**What the code does:**

1. `SessionService.cancel()` is called
2. It fetches the session record from MongoDB (a **lightweight** fetch — just the record, not the full graph with all its nodes and blueprints, which would be expensive and unnecessary)
3. It checks: **"Is this session QUEUED or RUNNING?"** If not, it rejects with 409 (conflict) — you can't cancel something that's already finished
4. It reads the `workflow_id` from the saved session tags (more on why this exists below)
5. It calls the `canceller.cancel(session_id, workflow_id)`

**Why not just update the database to CANCELLED right here?** Because that would mean two different places can change the session's lifecycle status — the API and the workflow. That creates race conditions. Instead, the API's only job is to *signal* the cancellation. The actual status change happens in one place only: the workflow's cleanup activity.

---

## Step 2: Tell Temporal to Cancel the Workflow (Outbound Adapter)

**What happens:** `TemporalSessionCanceller` calls `handle.cancel()` on the Temporal workflow.

**What this does:** It's just sending a message to Temporal saying "please cancel this workflow." It doesn't kill anything immediately — it's more like raising your hand and saying "stop."

**Why `handle.cancel()` specifically?**

- It's Temporal's official, built-in way to cancel a workflow
- Temporal propagates the cancellation **automatically** from the parent workflow (`SessionWorkflow`) to the child workflow (`GraphTraversalWorkflow`) — you don't need to cancel them separately
- It doesn't kill a running activity mid-execution (which would leave things in a broken state) — instead, it waits for the current activity to finish, then raises the error
- It's safe to call even if the workflow already finished (the adapter catches that exception and ignores it)

**What if Temporal is down?** The adapter catches the exception, logs a warning, and returns. The API still responds 200 to the user. The session continues running normally. The user can retry later.

---

## Step 3: Temporal Delivers `CancelledError` to the Workflow

**What happens:** Temporal raises a `CancelledError` exception inside the workflow at the **next await point** (the next time the workflow is waiting for something).

**When exactly does this happen? It depends on the stage:**

| Stage | What happens |
|---|---|
| Session is QUEUED (waiting in the task queue) | Workflow gets cancelled before it even starts. Cleanup runs immediately. |
| `begin_session` activity is running | The activity finishes (it's fast, ~200ms), then `CancelledError` is raised |
| Between supersteps (planning next nodes) | `CancelledError` is raised immediately. No new nodes are dispatched. |
| A node is executing (e.g., LLM API call) | The current LLM call **finishes naturally** (you don't want to kill a call mid-stream). After it returns, `CancelledError` is raised. No new nodes start. |

**Why does `CancelledError` bypass the runner's error handler?** This is a clever Python detail. `CancelledError` inherits from `BaseException`, not `Exception`. The existing `BackgroundSessionRunner` catches `Exception` (which catches failures), but `CancelledError` slips right through to the `SessionWorkflow` where the Temporal-specific cleanup lives. This means the domain-layer runner code **doesn't need any changes** — cancellation is handled entirely in the Temporal adapter layer.

---

## Step 4: Workflow Catches `CancelledError` and Runs Cleanup

**What happens:** `SessionWorkflow.run()` has a `try/except CancelledError` block. When caught, it runs `self.cancel()`, which executes the `cancel_session` **activity**.

**Why use a Temporal activity for cleanup (instead of inline code)?**

- Activities have Temporal's retry and timeout guarantees — if the cleanup fails, Temporal can retry it
- It runs on a worker, which has access to the database and Redis
- It follows the exact same pattern as `complete_session` and `fail_session` — consistency matters
- Even if someone cancels the workflow directly from Temporal's admin UI (bypassing the API entirely), this cleanup still runs

---

## Step 5: Cleanup Activity Does Two Things

The `cancel_session` activity calls `BackgroundLifecycleHandler.cancel(run_id)`, which does:

### 5a. Update the database

- Sets session status to `CANCELLED`
- Sets `finished_at` timestamp
- Saves to MongoDB

### 5b. Close the Redis streaming channel

Same 3 Redis commands used by `complete()` and `fail()`:

1. `XADD` a `{__control: "close"}` message to the stream — this tells the subscriber "we're done"
2. `SREM` the session from the active sessions set
3. `DELETE` the stream key

**Why reuse the existing `close()` method?** Zero new Redis logic. The same cleanup that happens when a session completes normally also happens on cancel. The subscriber code doesn't need any changes either — it already knows how to handle the `{__control: "close"}` signal.

---

## Step 6: Client Sees the Stream Close

The frontend's SSE/streaming reader receives the `{__control: "close"}` message and stops reading. The client can then check `GET /session.status` to see the status is `CANCELLED` (not `COMPLETED` or `FAILED`).

---

## How Other Paths Don't Overwrite CANCELLED

After the session is marked CANCELLED, there's a race condition risk: what if the `complete_session` or `fail_session` activity also tries to run? The `SessionLifecycle` class has **guards**:

```python
# Inside complete():
if record.status == CANCELLED:
    return  # do nothing

# Inside fail():
if record.status == CANCELLED:
    return  # do nothing
```

CANCELLED is a **terminal state**. Nothing can overwrite it.

---

## Why the Workflow ID Has a Random Suffix

When a user does "continue conversation," it creates a **new workflow** for the **same session**. Temporal requires unique workflow IDs, so each submission gets an ID like `session-abc123-7f3a9b1e` (session ID + random 8 chars). The workflow ID is saved in the session's tags when submitted, and read back from those tags when cancel is called. This avoids needing to generate predictable IDs.

---

## Summary — The Cancel Journey in One List

1. User clicks Stop -> `POST /session.cancel`
2. API checks eligibility (QUEUED/RUNNING) and reads the saved `workflow_id`
3. API tells Temporal: `handle.cancel()` (signal only, no DB write)
4. Temporal delivers `CancelledError` to the workflow at the next await point
5. Current running activity (if any) finishes naturally — nothing is killed mid-execution
6. Workflow catches `CancelledError`, runs `cancel_session` cleanup activity
7. Cleanup: status -> CANCELLED in MongoDB, Redis stream closed
8. Client sees stream close, checks status = CANCELLED
9. Any late `complete()`/`fail()` calls are no-ops (terminal state guard)

**The key principle: the API only signals, the workflow owns the lifecycle transition.** One owner, one source of truth, no race conditions.

---

## New Code & Modifications — File by File

### New Files

| File | What it introduces |
|---|---|
| `adapters/outbound/temporal/canceller.py` | **`TemporalSessionCanceller`** — the outbound adapter that calls Temporal's `handle.cancel()`. Takes a `session_id` and `workflow_id`, gets the workflow handle from the Temporal client, and sends the cancel signal. Catches and suppresses exceptions if the workflow already finished or Temporal is unreachable. |
| `adapters/temporal/models.py` *(new DTO)* | **`CancelSessionParams`** — a simple data transfer object that carries the `run_id` into the `cancel_session` activity. Same pattern as the existing `BeginSessionParams` / `CompleteSessionParams`. |

### Modified Files

#### Domain Layer (`lib/mas/`)

| File | What changes | Why |
|---|---|---|
| `lib/mas/session/domain/status.py` | Add `CANCELLED` to the `SessionStatus` enum | The system needs a new terminal state to distinguish "user stopped it" from COMPLETED or FAILED. |
| `lib/mas/session/execution/lifecycle.py` | Add `cancel(record)` method. Add guards in `complete()` and `fail()` to no-op if status is already CANCELLED. | `cancel()` sets the status to CANCELLED and marks `finished_at`. The guards prevent race conditions — once cancelled, nothing can overwrite it. |
| `lib/mas/session/execution/lifecycle_handler.py` | Add `cancel(run_id)` method to `BackgroundLifecycleHandler` | Orchestrates the cancel: calls `lifecycle.cancel(record)` to update the DB, then calls `_close_channel(run_id)` to clean up Redis. Same pattern as the existing `complete()` and `fail()` methods. |
| `lib/mas/session/execution/ports.py` | Add `BackgroundSessionCanceller` abstract port (interface) | Defines the contract for cancelling a background session. The domain layer uses this interface — it doesn't know or care that the implementation is Temporal. This is the hexagonal architecture pattern. |
| `lib/mas/session/execution/__init__.py` | Export `BackgroundSessionCanceller` | Makes the new port importable from the package. |
| `lib/mas/session/service.py` | Add `cancel(session_id)` method. Update constructor to accept a `canceller` parameter. | The service method that the API endpoint calls. Fetches the record, checks eligibility, reads the workflow_id from tags, and delegates to the canceller port. |

#### Temporal Adapter Layer (Inbound)

| File | What changes | Why |
|---|---|---|
| `adapters/inbound/temporal/workflows/session_workflow.py` | Add `try/except CancelledError` in `run()`. Add `cancel()` method that executes the `cancel_session` activity. | This is where the workflow catches Temporal's cancellation signal and triggers the cleanup activity. |
| `adapters/inbound/temporal/activities/session_lifecycle_activities.py` | Add `cancel_session` activity function | A new Temporal activity that calls `BackgroundLifecycleHandler.cancel(run_id)`. Mirrors the existing `begin_session`, `complete_session`, `fail_session` activities. |
| `adapters/inbound/temporal/worker.py` | Register the new `cancel_session` activity | The Temporal worker needs to know about the new activity so it can execute it when dispatched. |

#### Temporal Adapter Layer (Outbound)

| File | What changes | Why |
|---|---|---|
| `adapters/outbound/temporal/submitter.py` | Generate `workflow_id` with random suffix (`session-{run_id}-{uuid[:8]}`). Persist it in `record.run_context.tags["workflow_id"]`. | The canceller needs to know which Temporal workflow to cancel. The random suffix ensures uniqueness for "continue conversation" scenarios where the same session spawns multiple workflows. |

#### API Layer

| File | What changes | Why |
|---|---|---|
| `adapters/inbound/flask/endpoints/sessions.py` | Add `POST /session.cancel` endpoint | The HTTP entry point. Extracts `session_id` from the request, calls `SessionService.cancel()`, returns 200 on success or 409 if the session isn't cancellable. |

#### Bootstrap

| File | What changes | Why |
|---|---|---|
| `bootstrap/container.py` | Instantiate `TemporalSessionCanceller`. Pass it to `SessionService` constructor. | Wires the new canceller adapter into the dependency injection container so everything is connected at startup. |

---

### Visual Map — How the New Code Connects

```
POST /session.cancel  (sessions.py - NEW endpoint)
       │
       ▼
SessionService.cancel()  (service.py - NEW method)
       │
       ├── manager.get_record()          (existing - lightweight DB fetch)
       ├── status guard                  (NEW - check QUEUED/RUNNING)
       ├── read workflow_id from tags    (NEW - reads what submitter saved)
       │
       ▼
BackgroundSessionCanceller.cancel()  (ports.py - NEW interface)
       │
       ▼
TemporalSessionCanceller.cancel()  (canceller.py - NEW file)
       │
       ▼
handle.cancel()  ──► Temporal delivers CancelledError
                              │
                              ▼
                     SessionWorkflow.run()  (session_workflow.py - MODIFIED)
                       except CancelledError:
                         self.cancel()
                              │
                              ▼
                     cancel_session activity  (session_lifecycle_activities.py - NEW activity)
                              │
                              ▼
                     BackgroundLifecycleHandler.cancel()  (lifecycle_handler.py - NEW method)
                       ├── lifecycle.cancel(record)  (lifecycle.py - NEW method)
                       │     ├── status → CANCELLED
                       │     └── save to MongoDB
                       └── _close_channel(run_id)  (existing - same as complete/fail)
                             ├── XADD {__control: close}
                             ├── SREM from active set
                             └── DELETE stream
```

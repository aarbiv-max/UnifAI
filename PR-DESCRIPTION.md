# Stop/Cancel Button for Multi-Agent Chat

## TLDR

Added a Stop button to the multi-agent chat that lets users cancel a running session mid-execution. The cancel signal flows from the UI through the backend API to Temporal, which gracefully stops the workflow. The session is marked as `CANCELLED`, the chat displays "Session was stopped by user", and the graph shows in-progress agents as "Stopped" with a red indicator.

---

## What Changed

### Backend (Python / Temporal)

- New `CANCELLED` value in `SessionStatus` enum
- New `POST /session.cancel` endpoint — returns 409 if session is not cancellable (already completed/failed/cancelled)
- New `BackgroundSessionCanceller` abstract port with `TemporalSessionCanceller` adapter that calls `workflow_handle.cancel()`
- New `CancelSessionParams` model and `cancel_session` Temporal activity registered in the worker
- `SessionWorkflow.run()` catches both `asyncio.CancelledError` and wrapped `ChildWorkflowError → CancelledError` chains (via `_is_temporal_cancellation` helper), then executes the `cancel_session` activity
- `SessionLifecycle.cancel()` method sets status to `CANCELLED`, stamps `metadata.tags["cancelled"]`, and persists
- `complete()` and `fail()` lifecycle methods are now no-ops if session is already `CANCELLED` (prevents race conditions where a late completion overwrites the cancel)
- `BackgroundLifecycleHandler.cancel()` orchestrates lifecycle transition + Redis channel close
- Temporal workflow ID is saved in session metadata tags on submit (`service.py`) so the canceller can look it up later
- `UserSessionManager.save_record()` added to allow persisting records after context updates
- `SessionService` constructor now accepts an optional `BackgroundSessionCanceller`; `AppContainer` wires it for the Temporal engine
- `SessionChat` model and `MongoSessionRepository.fetch_chat()` now include `status` so the frontend knows session state when loading chat history
- `StreamStatusResponse` type updated to include `'cancelled'` as a valid status

### Frontend (React / TypeScript)

- **Send/Stop button swap** — the Send button is replaced with a Stop button (■ icon + animated dots) while a session is running (`isTyping || isLiveRequest`); shows a spinner while the cancel API call is in flight
- **Text input disabled** during execution to prevent submitting a new query mid-run
- **Cancel handling in ChatInterface** — `handleCancelClick` calls the parent's `onCancelSession`, sets `wasCancelledByUserRef` so both the success and error paths of `handleSendMessage` show "Session was stopped by user." instead of the normal final answer or error message
- **Stream-end detection** — when `isLiveRequest` flips to false and `wasCancelledByUserRef` is set, the streaming message is replaced with the cancellation notice (skips final-answer fetch)
- **Session reload** — when re-opening a session with `sessionStatus === "CANCELLED"`, the last AI message is overwritten with the cancellation notice; reconnection to the Redis stream is skipped for all terminal states (CANCELLED, FAILED, COMPLETED)
- **Reconnection guard in ChatInterface** — polling-based reconnection also skips sessions in terminal states
- **Graph visualization** — when execution ends after cancellation, in-progress nodes transition to `CANCELLED` (red glow, "Stopped" label), completed nodes stay "Done", and idle nodes stay idle. A "Session Stopped" red badge replaces the green "Complete" badge in the graph header
- **New `CANCELLED` visual style** in `GraphDisplayHelpers.ts` — red stroke, red glow SVG filter, "Stopped" label
- **`NodeStatus` type** extended with `"CANCELLED"` in `AgentNodeOverlay.tsx`
- **`ActiveNodesStatusBar`** shows red dot + "Stopped" for cancelled nodes
- **Public chat** — cancel wired through `usePublicChat` hook with `handleCancelSession` callback + `AbortController` on the fetch request to abort the HTTP stream client-side
- **`use-session-stream` hook** — new `cancelSessionExecution()` method that calls `POST /session.cancel` (silently swallows 409)
- **`use-session-management` hook** — `fetchSessionMessages` refactored to `fetchSessionChat` which returns both messages and status; `loadSessionMessages` now populates `session.status` on the `ChatSession` object
- **Type updates** — `Message.isCancelled` added to `chat/types.ts`; `ChatSession.status` and `SessionStateData.status` added to `types/session.ts`

---

## Cancel Flow

```text
User clicks Stop
  → ChatInterface.handleCancelClick()
    → ExecutionTab.handleCancelSession()
      → sessionStream.cancelSessionExecution(sessionId)  — POST /session.cancel
      → sessionStream.cancelStream()                     — close client-side SSE
      → setIsCancelled(true), setIsLiveRequest(false)
  → Backend: SessionService.cancel()
    → Validates status is QUEUED or RUNNING
    → Looks up workflow_id from session metadata tags
    → TemporalSessionCanceller.cancel(workflow_id)       — Temporal client cancel
  → Temporal raises CancelledError inside SessionWorkflow
    → Workflow catches it → executes cancel_session activity
    → BackgroundLifecycleHandler.cancel()
      → SessionLifecycle.cancel() → status = CANCELLED, stamps metadata
      → Closes Redis stream channel
  → UI receives stream end
    → wasCancelledByUserRef triggers "Session was stopped by user." message
    → GraphDisplay marks PROGRESS nodes as CANCELLED (red), DONE stays DONE, IDLE stays IDLE
```

---

## Files Changed

| Area | Files |
|------|-------|
| **API Endpoint** | `adapters/inbound/flask/endpoints/sessions.py` |
| **Domain Models** | `session/domain/status.py`, `session/domain/models.py` |
| **Session Service** | `session/service.py` |
| **Session Management** | `session/management/user_session_manager.py` |
| **Execution Ports** | `session/execution/ports.py`, `session/execution/__init__.py` |
| **Lifecycle** | `session/execution/lifecycle.py`, `session/execution/lifecycle_handler.py` |
| **Temporal Workflow** | `adapters/inbound/temporal/workflows/session_workflow.py` |
| **Temporal Activities** | `adapters/inbound/temporal/activities/session_lifecycle_activities.py` |
| **Temporal Worker** | `adapters/inbound/temporal/worker.py` |
| **Temporal Models** | `adapters/temporal/models.py` |
| **Outbound Adapters** | `adapters/outbound/temporal/canceller.py` (new), `adapters/outbound/mongo/session_repository.py` |
| **Bootstrap / DI** | `bootstrap/container.py` |
| **Shared Config** | `shared-resources/sso-backend/config/app_config.py` (minor formatting) |
| **UI Components** | `ChatInterface.tsx`, `ExecutionTab.tsx`, `PublicChat.tsx` |
| **UI Hooks** | `use-session-stream.ts`, `use-session-management.ts`, `use-public-chat.ts` |
| **UI Graph** | `GraphDisplay.tsx`, `GraphDisplayHelpers.ts`, `AgentNodeOverlay.tsx` |
| **UI Types** | `chat/types.ts`, `types/session.ts` |
| **UI API** | `api/sessions.ts` |
| **UI Config** | `vite.config.ts` (minor formatting) |

# Architecture Design Review (ADR) — Session Cancel: UI Integration

**Feature Name:** Session Cancel — Frontend Stop/Cancel Button for Multi-Agent Chat

**Lead Developer:** Yosi Habushi | **Date:** 2026-03-23 | **Priority:** High

**Related:** [ADR — Session Cancel: Temporal Workflow Execution Path (Backend)](ADR-Session-Cancel-Temporal-Workflow.html)

---

## 1. Executive Summary

| Section | Detail |
|---------|--------|
| **Problem Statement** | Once a user sends a query in the multi-agent chat, there is no way to stop the execution. The Send button is disabled during streaming (`isTyping`), and the `TypingIndicator` / `ChatOnlyLoader` displays indefinitely until the session completes or fails. The existing `cancelStream()` in `useSessionStream` only stops the **client-side** NDJSON reader — it does **not** cancel backend execution. Users must wait for the full graph traversal (potentially 30+ seconds with multiple LLM calls) to finish. |
| **High-Level Solution** | Add a **Stop button** that replaces the Send button while a session is actively running. Clicking it calls the new `POST /session.cancel` backend endpoint, handles the `session_cancelled` stream event, stops all client-side streaming, and displays a "Session cancelled" message. The solution touches 4 existing files and adds 1 new API function, following existing patterns (shadcn Button, lucide icons, axios calls, toast notifications, stream event handling). |
| **Success Metrics** | Stop button appears within 100ms of session start. Backend cancel API responds within 1 second. Stream closes immediately (user sees no further tokens). "Session cancelled" indication appears in the chat. Input re-enables for the next query. Works in both `ExecutionTab` (logged-in) and `PublicChat` (shared link) paths. |

---

## 2. Current State Analysis

### 2.1 — What Exists Today

| Concern | Current Behavior | File |
|---------|-----------------|------|
| **Send button** | Disabled while `isTyping` or blueprint invalid; always shows `Send` icon | `ChatInterface.tsx:1176-1182` |
| **Streaming indicator** | `TypingIndicator` (animated dots) or `ChatOnlyLoader` (spinner) shown during `isTyping` or `isLiveRequest` | `ChatInterface.tsx:1105-1109` |
| **Client cancel** | `cancelStream()` aborts the `ReadableStream` reader + `AbortController`; does NOT cancel backend | `use-session-stream.ts:96-107` |
| **Stream events** | Handles `heartbeat`, `stream_end`, `stream_error`; no `session_cancelled` handler | `use-session-stream.ts:163-180` |
| **Session status types** | `StreamStatusResponse.status: 'running' \| 'completed' \| 'failed' \| 'unknown'` — no `'cancelled'` | `api/sessions.ts:51-61` |
| **API layer** | `submitSession()`, `subscribeToSessionStream()`, `getSessionStreamStatus()` — no `cancelSession()` | `api/sessions.ts` |
| **Input gating** | Textarea disabled by `!blueprintExists \| isSharingDisabled \| !blueprintValid \| isValidatingBlueprint`; NOT by session status | `ChatInterface.tsx:1145` |

### 2.2 — What the Backend Provides (from Backend ADR)

| Backend API | Behavior |
|------------|----------|
| `POST /session.cancel` `{ sessionId }` | Returns `200 { sessionId, status: "CANCELLED" }` if cancelled, `409` if not in cancellable state |
| Redis stream event | `{ type: "session_cancelled" }` emitted on the session's Redis stream immediately |
| Redis stream close | `{ __control: "close" }` follows — reader stops (existing behavior) |
| Session status | `CANCELLED` is a new terminal status in the backend |

---

## 3. Proposed UI Changes

### 3.1 — Files to Change (5 files, 0 new files)

| # | File | Change |
|---|------|--------|
| 1 | `ui/client/src/api/sessions.ts` | Add `cancelSession()` API function + add `'cancelled'` to `StreamStatusResponse.status` type |
| 2 | `ui/client/src/hooks/use-session-stream.ts` | Handle `session_cancelled` event type in the NDJSON read loop |
| 3 | `ui/client/src/components/agentic-ai/chat/ChatInterface.tsx` | Replace Send button with Stop button during streaming; handle cancellation UI state |
| 4 | `ui/client/src/components/agentic-ai/ExecutionTab.tsx` | Wire cancel through `triggerExecution`; handle cancel in `onStreamEnd`/`onError` |
| 5 | `ui/client/src/hooks/use-public-chat.ts` | Add cancel support to the public chat `triggerExecution` path |

---

### 3.2 — Layer 1: API Client (`api/sessions.ts`)

**Add `cancelSession()` function** — follows the exact pattern of `submitSession()`:

```typescript
export interface CancelSessionResponse {
  sessionId: string;
  status: 'CANCELLED';
}

export async function cancelSession(sessionId: string): Promise<CancelSessionResponse> {
  const response = await axios.post('/sessions/session.cancel', { sessionId });
  return response.data;
}
```

**Update `StreamStatusResponse.status` type** to include `'cancelled'`:

```typescript
export interface StreamStatusResponse {
  session_id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled' | 'unknown';
  // ... rest unchanged
}
```

**Rationale:**
- Uses the same `axios` instance from `@/http/axiosAgentConfig` (baseURL `/api2`, 300s timeout).
- POST follows the same convention as `submitSession()`, `createSession()`.
- The `sessionId` field name matches the backend's `@from_body({"session_id": fields.Str(data_key="sessionId")})`.

---

### 3.3 — Layer 2: Stream Hook (`use-session-stream.ts`)

**Add `session_cancelled` to the event handling** in the NDJSON read loop, alongside `stream_end` and `stream_error`:

```typescript
// Inside the while(true) read loop, after heartbeat and stream_end checks:

if (event.type === 'session_cancelled') {
  setIsStreaming(false);
  onStreamEndRef.current?.();
  return;
}
```

**Add `cancelSession` to the hook's return interface and implementation:**

```typescript
export interface UseSessionStreamReturn {
  // ... existing fields ...
  cancelSession: (sessionId: string) => Promise<void>;
}
```

Implementation:

```typescript
const cancelSessionFn = useCallback(async (sessionId: string): Promise<void> => {
  try {
    await cancelSession(sessionId);
  } catch (err: any) {
    if (err.response?.status === 409) {
      // Session not in cancellable state — already completed/failed/cancelled
      return;
    }
    throw err;
  }
}, []);
```

**Why `session_cancelled` behaves like `stream_end`:**
- The backend emits `{ type: "session_cancelled" }` via `channel.emit()` and then immediately calls `channel.close()`.
- The reader will see `session_cancelled` (payload event) followed by `__control: close` (control event).
- The control event causes the existing reader to return/stop.
- However, the `session_cancelled` event arrives first as a payload. We treat it as a stream end so `onStreamEnd` fires immediately — the reader doesn't need to wait for the close control.
- The subsequent close control is handled naturally by the existing reader loop termination.

**Why we don't need a new `onCancelled` callback:**
- From the UI's perspective, `session_cancelled` and `stream_end` have the same effect: stop streaming, clean up, show final state. The difference is in what message we display — and that logic lives in `ChatInterface` (Layer 3), which knows whether a cancel was user-initiated.

---

### 3.4 — Layer 3: Chat Interface (`ChatInterface.tsx`)

This is the primary UI change. Three aspects:

#### 3.4.1 — Stop Button (replaces Send during streaming)

**New prop:**

```typescript
interface ChatInterfaceProps {
  // ... existing props ...
  onCancelSession?: () => Promise<void>;  // Called when user clicks Stop
}
```

**Button swap logic** — the Send button area becomes conditional:

```
CONDITION                           BUTTON SHOWN
──────────────────────────────────────────────────────
isTyping || isLiveRequest           Stop button (Square icon, red accent)
otherwise                           Send button (Send icon, primary)
```

**Stop button implementation** using existing patterns:

```tsx
import { Square } from "lucide-react";  // lucide "stop" icon

// State for cancel-in-progress
const [isCancelling, setIsCancelling] = useState(false);

{(isTyping || isLiveRequest) ? (
  <Button
    onClick={handleCancelClick}
    disabled={isCancelling}
    className="bg-red-600 hover:bg-red-700 mb-0"
    title="Stop generation"
  >
    {isCancelling ? (
      <Loader2 className="h-4 w-4 animate-spin" />
    ) : (
      <Square className="h-4 w-4" />
    )}
  </Button>
) : (
  <Button
    onClick={() => handleSendMessage()}
    disabled={inputMessage.trim() === "" || isTyping || !blueprintExists || ...}
    className="bg-primary hover:bg-[#7525c9] mb-0"
  >
    <Send className="h-4 w-4" />
  </Button>
)}
```

**Design rationale:**
- `Square` icon from `lucide-react` (already in project dependencies) is the standard "stop" icon used across AI chat products.
- Red accent (`bg-red-600`) distinguishes it from the primary Send action.
- `Loader2 animate-spin` during `isCancelling` reuses the existing loading pattern (same as `ChatOnlyLoader`).
- The `UmamiTrack` wrapper remains around the button for analytics.

#### 3.4.2 — Cancel Click Handler

```typescript
const handleCancelClick = async () => {
  if (isCancelling) return;
  setIsCancelling(true);

  try {
    await onCancelSession?.();
  } catch (error) {
    console.error('Error cancelling session:', error);
    toast({
      title: "Cancel Failed",
      description: "Failed to cancel the session. It may have already completed.",
      variant: "destructive",
    });
  } finally {
    setIsCancelling(false);
  }
};
```

#### 3.4.3 — Cancellation Message in Chat

When a session is cancelled, the placeholder AI message should show a cancellation indication instead of remaining empty or showing a generic error:

```typescript
// New state to track if current session was cancelled by user
const [wasCancelledByUser, setWasCancelledByUser] = useState(false);
```

When `isLiveRequest` becomes `false` after a cancel:

```typescript
// In the existing useEffect that handles !isLiveRequest && currentStreamingMessageId:
if (!isLiveRequest && currentStreamingMessageId) {
  const messageId = currentStreamingMessageId;
  const wasReconnection = isReconnectionStreamRef.current;
  const wasCancelled = wasCancelledByUser;

  stopStreamingLogs(messageId);
  setCurrentStreamingMessageId(null);
  isReconnectionStreamRef.current = false;
  setWasCancelledByUser(false);

  if (wasCancelled) {
    // Show cancellation message on the AI placeholder
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id === messageId) {
          return {
            ...msg,
            content: "Session was stopped by user.",
            isCancelled: true,  // New optional field on Message type
          };
        }
        return msg;
      })
    );
    return;  // Skip fetching final answer
  }

  // ... existing reconnection/completion logic ...
}
```

#### 3.4.4 — Cancelled Message Rendering

The cancelled message should be visually distinct. Using existing styling patterns:

```tsx
{message.isCancelled && (
  <div className="flex items-center gap-2 text-gray-400 text-sm italic">
    <Square className="h-3.5 w-3.5" />
    <span>{message.content}</span>
  </div>
)}
```

#### 3.4.5 — Input Re-enablement After Cancel

No special logic needed. The existing flow handles this:
1. `handleCancelClick` calls `onCancelSession` (which calls `cancelSession` API + `cancelStream`)
2. The stream receives `session_cancelled` → `onStreamEnd` fires
3. `ExecutionTab.onStreamEnd` sets `isLiveRequest(false)`
4. `isTyping` is reset when `triggerExecution` resolves (the `streamCompletePromise` resolves)
5. Both `isTyping` and `isLiveRequest` become `false` → Send button reappears, textarea is interactive

---

### 3.5 — Layer 4: ExecutionTab (`ExecutionTab.tsx`)

**Wire the cancel function** through the session stream hook and pass it to `ChatInterface`:

```typescript
// In triggerExecution or as a separate handler:
const handleCancelSession = useCallback(async () => {
  if (!selectedSession?.id) return;

  // 1. Call backend cancel API
  await sessionStream.cancelSession(selectedSession.id);

  // 2. Cancel client-side stream subscription
  sessionStream.cancelStream();

  // 3. Stream end will be triggered by the session_cancelled event
  //    or by cancelStream() closing the reader
  setIsLiveRequest(false);
}, [selectedSession, sessionStream]);
```

**Pass to ChatInterface:**

```tsx
<ChatInterface
  key={selectedSession?.id || 'no-session'}
  runId={selectedSession?.id || ''}
  triggerExecution={triggerExecution}
  onCancelSession={handleCancelSession}  // NEW
  initialMessages={currentSessionMessages}
  // ... other existing props
/>
```

**`triggerExecution` update — handle cancel resolution:**

The existing `triggerExecution` awaits `streamCompletePromise`, which is resolved by `onStreamEnd`. Since `session_cancelled` triggers `onStreamEnd`, the promise resolves naturally. The subsequent `session.chat.get` may return partial output or empty — both are fine:

```typescript
const triggerExecution = async (sessionPayload: SessionPayload): Promise<string> => {
  try {
    setIsLiveRequest(true);

    const streamCompletePromise = new Promise<void>((resolve) => {
      streamCompleteResolverRef.current = resolve;
    });

    await sessionStream.submitAndSubscribe({ ... });
    await streamCompletePromise;

    // After cancel, session.chat.get may return empty output — that's expected
    const session_response = await axios.get(
      `/sessions/session.chat.get?sessionId=${sessionPayload.sessionId}`
    );
    return session_response.data.output || '';  // Handle empty output gracefully
  } catch (error) {
    console.error('Error in session execution:', error);
    setIsLiveRequest(false);
    throw error;
  }
};
```

---

### 3.6 — Layer 5: Public Chat (`use-public-chat.ts`)

The public chat flow uses a different `triggerExecution` that calls `fetch` directly (not `useSessionStream`). It needs its own cancel path:

```typescript
// Add to usePublicChat:
const [abortController, setAbortController] = useState<AbortController | null>(null);

const handleCancelSession = useCallback(async () => {
  if (!runId) return;

  // Cancel the fetch stream
  abortController?.abort();

  // Call backend cancel API
  await cancelSession(runId);
}, [runId, abortController]);
```

And expose `handleCancelSession` in the return value for `PublicChat` to pass as `onCancelSession` to `ChatInterface`.

---

## 4. UI State Machine

All possible UI states and transitions for the chat input area:

```
                              ┌───────────────┐
                              │     IDLE       │
                              │                │
                              │  Send button   │
                              │  (enabled if   │
                              │   input valid) │
                              └──────┬────────┘
                                     │
                              User clicks Send
                                     │
                              ┌──────▼────────┐
                              │   SUBMITTING   │
                              │                │
                              │  Stop button   │
                              │  isTyping=true │
                              │  TypingIndicator│
                              │  Input disabled│
                              └──────┬────────┘
                                     │
                              Submit + subscribe
                              completes
                                     │
                              ┌──────▼────────┐
                              │   STREAMING    │
                              │                │
                              │  Stop button   │
                              │  isLiveRequest │
                              │  Stream logs   │
                              │  updating      │
                              └──┬──────────┬──┘
                                 │          │
                    User clicks  │          │  Stream ends
                    Stop button  │          │  (stream_end)
                                 │          │
                          ┌──────▼──┐  ┌────▼──────────┐
                          │CANCELLING│  │  COMPLETING    │
                          │          │  │                │
                          │ Stop btn │  │  Fetching      │
                          │ spinner  │  │  final answer  │
                          │ API call │  │                │
                          └──────┬───┘  └────┬──────────┘
                                 │           │
                          session_cancelled   │
                          event received      │
                                 │           │
                          ┌──────▼───┐  ┌────▼──────────┐
                          │CANCELLED  │  │  COMPLETED     │
                          │           │  │                │
                          │ "Session  │  │  Final answer  │
                          │  stopped" │  │  displayed     │
                          │ message   │  │                │
                          │           │  │                │
                          │ Send btn  │  │  Send button   │
                          │ returns   │  │  returns       │
                          └───────────┘  └────────────────┘

                          ERROR PATH (at any streaming state):

                          ┌──────────────┐
                          │   ERRORED     │
                          │               │
                          │  Error toast  │
                          │  or inline    │
                          │  error msg    │
                          │               │
                          │  Send button  │
                          │  returns      │
                          └───────────────┘
```

---

## 5. Stream Event Handling — Full Matrix

How each stream event type is handled in `use-session-stream.ts`:

| Event Type | Current Handling | After Change |
|-----------|-----------------|--------------|
| `heartbeat` | `continue` (skip) | No change |
| `stream_end` | `setIsStreaming(false)`, call `onStreamEnd` | No change |
| `stream_error` | Call `onError(event.error)`, `setIsStreaming(false)` | No change |
| `session_cancelled` | **Not handled** — passed to `onChunk` as a regular event | **NEW:** `setIsStreaming(false)`, call `onStreamEnd` — treated as a clean stream end |
| All other events | Passed to `processEventData` → `onChunk` | No change |

---

## 6. Edge Cases and Race Conditions

| Scenario | UI Behavior | Implementation Detail |
|----------|------------|----------------------|
| User clicks Stop, then stream_end arrives simultaneously | Cancel API may return 409 (already completed). `isCancelling` resets, final answer shown normally. | `cancelSession` silently handles 409. `wasCancelledByUser` may be true but `session.chat.get` returns valid output — show it. |
| User clicks Stop during `isTyping` (before stream starts) | Cancel API called. If session hasn't been submitted yet, API returns 409 (PENDING). Toast shown. | Guard: only call cancel if `runId` exists and session has been submitted. |
| User clicks Stop, backend is down | Cancel API call fails. Toast: "Failed to cancel". Stream continues until natural end or timeout. | `handleCancelClick` catch block shows destructive toast. Stream reader not cancelled (backend still running). |
| User clicks Stop twice rapidly | First click sets `isCancelling=true`, disabling the button. Second click ignored. | `disabled={isCancelling}` on Stop button. |
| User switches session while cancelling | `cancelStream()` is called by session switching logic. Cancel API call may still be in flight. | Cancel API response is ignored (fire-and-forget semantics). New session loads normally. |
| `session_cancelled` arrives from backend without user clicking Stop (e.g., admin cancel) | Stream ends, `onStreamEnd` fires, AI message shows empty (no final answer). | Same as stream_end. No special handling needed — the user didn't request it, so no "Session stopped" message. |
| User navigates away and back to a cancelled session | `checkAndReconnect` calls `getSessionStreamStatus`. Status is `'cancelled'` or stream not active. Returns `false`. | Session shows as completed with whatever messages were saved. No reconnection attempted. |
| Network disconnection during cancel | Cancel API fails. Client-side stream reader may also fail. Both show error handling. | Existing error handling in `handleCancelClick` and `subscribeToStream` catch blocks. |
| Cancel during reconnection stream | User reconnected to active stream, then clicks Stop. Same cancel flow applies. | `isReconnectionStreamRef.current` is true. Cancel API called. Stream ends. Reconnection message shows "Session stopped". |

---

## 7. Component Hierarchy and Data Flow

```
ExecutionTab
├── useSessionStream hook
│   ├── submitAndSubscribe()     → POST /user.session.submit + GET /session.subscribe
│   ├── cancelStream()           → Abort client-side reader
│   ├── cancelSession()          → POST /session.cancel (NEW)
│   └── onChunk / onStreamEnd   → Callbacks for stream events
│
├── handleCancelSession()        → cancelSession() + cancelStream() + setIsLiveRequest(false)
│
├── triggerExecution()           → submitAndSubscribe + await streamComplete + session.chat.get
│
└── ChatInterface
    ├── handleSendMessage()      → triggerExecution()
    ├── handleCancelClick()      → onCancelSession() prop (NEW)
    │
    ├── SEND AREA (conditional):
    │   ├── isTyping || isLiveRequest → Stop Button (Square icon, red)
    │   └── otherwise                 → Send Button (Send icon, primary)
    │
    ├── STREAMING INDICATORS:
    │   ├── TypingIndicator          → Animated dots (normal mode)
    │   └── ChatOnlyLoader           → Spinner (chat-only mode)
    │
    └── MESSAGE DISPLAY:
        ├── Normal AI message        → StreamLogDisplay + finalAnswer
        ├── Cancelled AI message     → "Session was stopped by user." (NEW)
        └── Error AI message         → Error text (existing)
```

---

## 8. Accessibility

| Concern | Implementation |
|---------|---------------|
| **Stop button label** | `title="Stop generation"` + `aria-label="Stop generation"` |
| **Cancel state** | `aria-busy="true"` on the message area during cancellation |
| **Keyboard** | Stop button focusable via Tab, activatable via Enter/Space (default `<Button>` behavior) |
| **Screen reader** | Status message "Session was stopped" should use `role="status"` or `aria-live="polite"` |

---

## 9. Visual Specification

### 9.1 — Stop Button

```
┌──────────────────────────────────────────────────────────────────┐
│  Chat Interface                                                  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  [User Message]                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  ✨ AI Generated                                          │   │
│  │  ┌─ Agent Thinking ──────────────────────────────────┐    │   │
│  │  │  🔵 Orchestrator Agent     ⟳ Processing...        │    │   │
│  │  │  🔵 Research Agent         ⟳ Processing...        │    │   │
│  │  └────────────────────────────────────────────────────┘    │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────┐ ┌────────┐  │
│  │  Ask your AI assistant a question...            │ │ ■ Stop │  │
│  └─────────────────────────────────────────────────┘ └────────┘  │
│                                                       (red bg)   │
└──────────────────────────────────────────────────────────────────┘
```

### 9.2 — After Cancellation

```
┌──────────────────────────────────────────────────────────────────┐
│  Chat Interface                                                  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  [User Message]                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  ✨ AI Generated                                          │   │
│  │  ┌─ Agent Thinking ──────────────────────────────────┐    │   │
│  │  │  ✅ Orchestrator Agent     Complete                │    │   │
│  │  │  ■  Research Agent         Stopped                 │    │   │
│  │  └────────────────────────────────────────────────────┘    │   │
│  │                                                           │   │
│  │  ■ Session was stopped by user.                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────┐ ┌────────┐  │
│  │  Ask your AI assistant a question...            │ │ ➤ Send │  │
│  └─────────────────────────────────────────────────┘ └────────┘  │
│                                                      (primary)   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 10. Implementation Order

Recommended implementation sequence (dependency chain):

```
1. api/sessions.ts
   ├── Add cancelSession() function
   └── Update StreamStatusResponse type

2. hooks/use-session-stream.ts
   ├── Handle session_cancelled event
   └── Add cancelSession to hook return

3. components/agentic-ai/ExecutionTab.tsx
   ├── Add handleCancelSession callback
   └── Pass onCancelSession to ChatInterface

4. components/agentic-ai/chat/ChatInterface.tsx
   ├── Add onCancelSession prop
   ├── Add Stop button (conditional render)
   ├── Add handleCancelClick handler
   ├── Add isCancelling + wasCancelledByUser state
   ├── Update message display for cancelled messages
   └── Update Message type with isCancelled field

5. hooks/use-public-chat.ts
   ├── Add handleCancelSession for public path
   └── Wire through PublicChat component
```

---

## 11. Key Design Decisions

### 11.1 — Stop Button Replaces Send (Not Alongside)

**Decision:** The Stop button occupies the same position as the Send button (conditional render), rather than appearing as a separate button.

**Rationale:**
- Follows the pattern used by ChatGPT, Claude, and other AI chat products — users expect the action button to contextually change.
- Avoids cluttering the input area with multiple buttons.
- The Send button is already disabled during streaming, so showing it alongside Stop would be confusing.
- Single-button area keeps the existing layout unchanged.

### 11.2 — `session_cancelled` Treated as `stream_end` (Not as Error)

**Decision:** The `session_cancelled` stream event triggers `onStreamEnd`, not `onError`.

**Rationale:**
- Cancellation is a user-initiated intentional action, not a failure.
- Using `onError` would trigger error toast notifications and error message styling — wrong UX.
- The `onStreamEnd` path cleanly resolves the `streamCompletePromise` in `triggerExecution`, allowing the execution flow to complete gracefully.
- The distinction between "cancelled" and "completed" is handled in `ChatInterface` via the `wasCancelledByUser` flag, not at the stream level.

### 11.3 — Cancel is Fire-and-Forget from UI Perspective

**Decision:** After the cancel API returns 200, the UI immediately transitions to cancelled state. It does not wait for the `session_cancelled` stream event.

**Rationale:**
- The backend marks `CANCELLED` in the DB immediately (before Temporal cancel).
- Redis emits `session_cancelled` almost instantly (~1-5ms after API call).
- However, the NDJSON reader polls with XREAD block timeout (up to 5 seconds). The user shouldn't wait for the next XREAD cycle.
- Calling `cancelStream()` after the API call stops the client reader immediately.
- If `session_cancelled` arrives before `cancelStream()`, it's handled by the new event handler and stops the stream that way — either path leads to the same end state.

### 11.4 — No Confirmation Dialog for Cancel

**Decision:** Clicking Stop immediately cancels. No "Are you sure?" dialog.

**Rationale:**
- Speed is critical — users click Stop because they want to stop NOW.
- The action is not destructive: the user can simply send a new query.
- A confirmation dialog on a Stop button is unusual and feels heavy.
- The session's partial state is preserved in the DB (all completed supersteps), so no data is lost.

### 11.5 — Message Type Extension (`isCancelled` field)

**Decision:** Add an optional `isCancelled?: boolean` to the `Message` type rather than using a special `content` string.

**Rationale:**
- Enables distinct rendering (gray italic with stop icon) rather than being treated as regular AI text.
- Prevents issues with markdown rendering of the cancellation message.
- Follows the same pattern as `finalAnswer` — an optional field that changes rendering behavior.
- Doesn't break existing message serialization or history loading.

---

## 12. Testing Checklist

| Test Case | Expected Result |
|-----------|----------------|
| Send message → Stop button appears | Stop button visible with red background and Square icon |
| Click Stop → Session cancels | API called, stream stops, "Session stopped" message, Send button returns |
| Click Stop while `isTyping` (pre-stream) | If session submitted: cancels. If not yet submitted: toast error |
| Double-click Stop | Second click ignored (button disabled during `isCancelling`) |
| Cancel completes → Send new message | New message sends normally, new session execution works |
| Switch session while streaming → Stop button state | Stop button disappears (new session is idle), previous session continues in background |
| Reconnect to active session → Stop button | Stop button appears on reconnection (`isLiveRequest=true`) |
| Cancel during reconnection | Same cancel flow, "Session stopped" message on reconnect placeholder |
| Backend returns 409 (session already done) | Cancel treated as success (silent), final answer shown if available |
| Backend unavailable | Error toast: "Failed to cancel the session" |
| Public chat → Stop button | Same behavior via `usePublicChat.handleCancelSession` |
| Cancel → Reload page → View session | Session shows as cancelled/completed, messages from before cancel preserved |

---

## 13. Reviewer's Feedback

| Status | Feedback / Required Changes |
|--------|---------------------------|
| **[ ] Approved** | |
| **[ ] Revise** | |

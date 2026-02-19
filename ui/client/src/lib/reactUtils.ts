import { flushSync } from "react-dom";

/**
 * Runs `fn` synchronously within React's commit phase when possible.
 * Falls back to a normal invocation if flushSync throws (e.g. when called
 * during an already-flushing render or when the SVG context is invalid).
 */
export function safeFlushSync(fn: () => void): void {
  try {
    flushSync(fn);
  } catch (err) {
    console.warn("[safeFlushSync] flushSync failed, falling back to batched update:", err);
    fn();
  }
}

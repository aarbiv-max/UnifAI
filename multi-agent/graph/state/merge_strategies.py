from typing import Any, Dict, List, Sequence, Optional
from itertools import islice
from elements.llms.common.chat.message import ChatMessage, Role


def merge_string_dicts(existing: Dict[str, str], new_item: Any) -> Dict[str, str]:
    """
    Merge strategy for Dict[str, str]:
    - Accepts new_item as dict[str, str]
    - Overwrites or adds keys
    - Returns merged result
    """
    if not isinstance(existing, dict):
        existing = {}
    if isinstance(new_item, dict):
        # filter only str->str keys for safety
        merged = existing.copy()
        for k, v in new_item.items():
            if isinstance(k, str) and isinstance(v, str):
                merged[k] = v
        return merged
    return existing


def merge_dynamic_fields(
        existing: Dict[str, Any], new_values: Any
) -> Dict[str, Any]:
    """
    Simply updates `existing` with `new_values` if it’s a dict.
    """
    if not isinstance(existing, dict):
        existing = {}
    if isinstance(new_values, dict):
        existing.update(new_values)
    return existing


def _to_chat(msg: Any):
    """Single-pass conversion to ChatMessage (or None)."""
    if isinstance(msg, ChatMessage):
        return msg
    if isinstance(msg, dict) and "role" in msg and "content" in msg:
        return ChatMessage(**msg)
    if isinstance(msg, str):
        return ChatMessage(role=Role.ASSISTANT, content=msg)
    return None


def _same_history(a: Sequence[ChatMessage], b: Sequence[ChatMessage]) -> bool:
    """
    True when *all* messages in `a` equal the messages at the same positions in `b`.
    Works because dataclasses give ChatMessage a value-based __eq__.
    """
    return all(x == y for x, y in zip(a, islice(b, len(a))))


def append_chat_messages(
        existing: Optional[List[ChatMessage]],
        new_item: Any
) -> List[ChatMessage]:
    """
    Smart-merge for the `messages` channel.

    • Accepts `ChatMessage`, str, dict, list/tuple[…].
    • **If the node returned the full history**
      (i.e. new list starts with all the old messages in the same order)
      → replace the channel with that list.
    • Otherwise **treat the input as incremental** and simply append.
    • No cross-list de-duplication – duplicates are kept intentionally
      so `[x, y, z] + x` becomes `[x, y, z, x]`.
    """
    existing = existing or []
    # Normalise to a list[ChatMessage]
    raw_list = new_item if isinstance(new_item, (list, tuple)) else [new_item]
    incoming: List[ChatMessage] = [
        cm for cm in (_to_chat(r) for r in raw_list) if cm is not None
    ]

    if not incoming:
        return existing

    # ── Case A: node returned the *entire* history ──────────────────────────
    # e.g. existing = [x, y, z] • incoming = [x, y, z, x]
    #      → keep incoming as the new canonical history.
    if len(incoming) >= len(existing) and _same_history(existing, incoming):
        return incoming

    # ── Case B: node returned *only the new* messages ───────────────────────
    return existing + incoming

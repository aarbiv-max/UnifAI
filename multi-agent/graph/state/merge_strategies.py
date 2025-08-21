from typing import Any, Dict, List, Sequence, Optional, Union
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
    Simply updates `existing` with `new_values` if it's a dict.
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


def append_iem_packets(
        existing: Optional[List],
        new_item: Union[List, Any]
) -> List:
    """
    Merge strategy for IEM packets channel.
    
    • Appends new packets while avoiding duplicates by packet ID
    • Maintains insertion order
    • Handles both single packets and lists of packets
    """
    existing = existing or []

    # Normalize new_item to list
    if isinstance(new_item, list):
        incoming = new_item
    else:
        incoming = [new_item] if new_item is not None else []

    # Filter out None values and non-IEMPacket types
    valid_incoming = [p for p in incoming if p is not None and hasattr(p, 'id')]

    if not valid_incoming:
        return existing

    # Track existing packet IDs to avoid duplicates
    existing_ids = {getattr(p, 'id', None) for p in existing if hasattr(p, 'id')}

    # Append only new packets
    result = list(existing)
    for packet in valid_incoming:
        if packet.id not in existing_ids:
            result.append(packet)
            existing_ids.add(packet.id)

    return result


def merge_task_threads(
        existing: Optional[Dict[str, List[ChatMessage]]],
        new_item: Union[Dict[str, List[ChatMessage]], Any]
) -> Dict[str, List[ChatMessage]]:
    """
    Merge strategy for task_threads channel.
    
    Structure: {thread_id: [ChatMessage, ...]}
    
    • Task-focused conversation management
    • Merges conversation lists by thread ID
    • Reuses append_chat_messages logic for smart duplicate detection per thread
    • Clean separation by task execution context
    """
    existing = existing or {}

    if not isinstance(new_item, dict):
        return existing

    # Deep copy existing to avoid mutation
    result = {}
    for thread_id, messages in existing.items():
        result[thread_id] = list(messages) if messages else []

    # Merge new task thread conversations using append_chat_messages logic
    for thread_id, new_messages in new_item.items():
        if not isinstance(new_messages, list):
            continue

        # Get existing messages for this thread (or empty list)
        existing_thread_messages = result.get(thread_id, [])

        # Use append_chat_messages to handle smart merging for this thread
        merged_messages = append_chat_messages(existing_thread_messages, new_messages)

        # Update result with merged messages
        result[thread_id] = merged_messages

    return result


def merge_threads(
        existing: Optional[Dict[str, Any]],
        new_item: Union[Dict[str, Any], Any]
) -> Dict[str, Any]:
    """
    Merge strategy for threads channel.
    
    Structure: {thread_id: Thread}
    
    • Thread metadata management
    • Overwrites existing threads with new data
    • Preserves existing threads not in new_item
    """
    existing = existing or {}
    
    if not isinstance(new_item, dict):
        return existing
    
    # Create result by copying existing
    result = existing.copy()
    
    # Overwrite with new thread data
    for thread_id, thread_data in new_item.items():
        result[thread_id] = thread_data
    
    return result


def merge_workspaces(
        existing: Optional[Dict[str, Any]],
        new_item: Union[Dict[str, Any], Any]
) -> Dict[str, Any]:
    """
    Merge strategy for workspaces channel.
    
    Structure: {thread_id: Workspace}
    
    • Workspace data management
    • Overwrites existing workspaces with new data
    • Preserves existing workspaces not in new_item
    """
    existing = existing or {}
    
    if not isinstance(new_item, dict):
        return existing
    
    # Create result by copying existing
    result = existing.copy()
    
    # Overwrite with new workspace data
    for thread_id, workspace_data in new_item.items():
        result[thread_id] = workspace_data
    
    return result

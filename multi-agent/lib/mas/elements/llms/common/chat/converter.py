import logging
from datetime import datetime, timezone
from typing import List

from mas.elements.llms.common.chat.message import ChatMessage, Role, ToolCall
from mas.elements.llms.common.file_reference import FILE_EXPIRY_HOURS, FileState
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from .utils import ensure_tool_call_id

logger = logging.getLogger(__name__)


class LangChainConverter:
    """Translates between ChatMessage and LangChain messages."""

    @staticmethod
    def to_lc(
        history: List[ChatMessage],
        *,
        supports_multimodal: bool = False,
    ) -> List:
        """Convert ChatMessage list to LangChain messages.

        When *supports_multimodal* is True and a USER message carries
        file_references, the output ``HumanMessage`` uses a list of
        content parts (text + media) so the LLM receives the files natively.
        """
        out = []
        for m in history:
            if m.role == Role.SYSTEM:
                out.append(SystemMessage(content=m.content))

            elif m.role == Role.USER:
                content = m.content
                if supports_multimodal and m.file_references:
                    content = LangChainConverter._build_multimodal_content(m)
                out.append(HumanMessage(content=content))

            elif m.role == Role.ASSISTANT:
                if m.tool_calls:
                    tool_calls = [{
                        "name": tc.name,
                        "args": tc.args,
                        "id": tc.tool_call_id,
                        "type": "tool_call"
                    } for tc in m.tool_calls]
                    out.append(AIMessage(
                        content=m.content if m.content else "[TOOL CALL]",
                        tool_calls=tool_calls,
                        additional_kwargs=m.additional_kwargs or {}
                    ))
                else:
                    out.append(AIMessage(content=m.content))

            elif m.role == Role.TOOL:
                tool_name = getattr(m, 'name', None) or 'unknown_tool'
                out.append(ToolMessage(content=m.content, tool_call_id=m.tool_call_id, name=tool_name))

            else:
                raise ValueError(f"Unknown role {m.role}")
        return out

    @staticmethod
    def _build_multimodal_content(m: ChatMessage):
        """Build a list of content parts (text + media) for a USER message."""
        now = datetime.now(timezone.utc)
        active_refs = []
        expired_names = []

        for ref in (m.file_references or []):
            age_hours = (now - ref.uploaded_at).total_seconds() / 3600
            if age_hours > FILE_EXPIRY_HOURS or ref.state != FileState.ACTIVE:
                expired_names.append(ref.display_name)
            else:
                active_refs.append(ref)

        text = m.content
        if expired_names:
            text += f"\n[Expired files not included: {', '.join(expired_names)}]"

        if not active_refs:
            return text

        parts: list = [{"type": "text", "text": text}]
        for ref in active_refs:
            parts.append({
                "type": "media",
                "file_uri": ref.file_uri,
                "mime_type": ref.mime_type,
            })
        return parts

    @staticmethod
    def from_lc_message(m) -> ChatMessage:
        if isinstance(m, SystemMessage):
            return ChatMessage(role=Role.SYSTEM, content=m.content)

        elif isinstance(m, HumanMessage):
            content = m.content
            if isinstance(content, list):
                text_parts = []
                dropped = 0
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        text_parts.append(part)
                    else:
                        dropped += 1
                if dropped:
                    logger.debug(
                        "Dropped %d non-text parts from HumanMessage during from_lc conversion",
                        dropped,
                    )
                content = " ".join(text_parts) if text_parts else ""
            return ChatMessage(role=Role.USER, content=content)

        elif isinstance(m, AIMessage):
            tool_calls = None

            if getattr(m, "tool_call_chunks", None) and m.type == "tool_call_chunk":
                tool_calls = [ensure_tool_call_id(tc) for tc in m.tool_call_chunks]
            elif getattr(m, "tool_calls", None):
                tool_calls = [ensure_tool_call_id(tc) for tc in m.tool_calls]

            return ChatMessage(
                role=Role.ASSISTANT,
                content=m.content or " " if tool_calls else m.content,
                tool_calls=[ToolCall(**tc.model_dump()) for tc in tool_calls] if tool_calls else None,
                additional_kwargs=getattr(m, 'additional_kwargs', None)
            )

        elif isinstance(m, ToolMessage):
            return ChatMessage(role=Role.TOOL,
                               content=m.content,
                               tool_call_id=m.tool_call_id)

        else:
            raise ValueError(f"Unknown message type: {type(m)}")

    @staticmethod
    def from_lc(lc_msgs: List) -> List[ChatMessage]:
        return [LangChainConverter.from_lc_message(m) for m in lc_msgs]

from typing import Any, Dict, List, Optional, Iterator, Union
import copy
from uuid import uuid4
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import _chat_with_retry
from ..common.base_llm import BaseLLM
from mas.core.contracts import SupportsStreaming
from ..common.chat.converter import LangChainConverter
from ..common.chat.message import ChatMessage, Role, ToolCall
from ...tools.common.base_tool import BaseTool
from .tools_converter import GoogleGenAIToolsConverter


def _extract_text_content(content: Any) -> str:
    """
    Extract text from Google GenAI content which can be:
    - A simple string
    - A list of content blocks like [{'type': 'text', 'text': '...'}]
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return "".join(texts)
    return str(content)


class GoogleGenAILLM(BaseLLM, SupportsStreaming):
    """
    LLM client for Google Generative AI (Gemini) using LangChain's ChatGoogleGenerativeAI wrapper.
    """

    def __init__(
            self,
            model_name: str,
            api_key: str,
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
            top_p: Optional[float] = None,
            top_k: Optional[int] = None,
            **extra: Any
    ):
        """
        :param model_name:   Gemini model ID (e.g. "gemini-2.0-flash", "gemini-2.5-pro").
        :param api_key:      Google API key for Generative AI.
        :param temperature:  Sampling temperature.
        :param max_tokens:   Max tokens to generate (None for model default).
        :param top_p:        Top-p sampling parameter.
        :param top_k:        Top-k sampling parameter.
        :param extra:        Extra kwargs passed to ChatGoogleGenerativeAI.
        """
        self._name = "google-genai"

        client_kwargs: Dict[str, Any] = {
            "model": model_name,
            "google_api_key": api_key,
            "temperature": temperature,
            **extra
        }

        if max_tokens is not None:
            client_kwargs["max_output_tokens"] = max_tokens
        if top_p is not None:
            client_kwargs["top_p"] = top_p
        if top_k is not None:
            client_kwargs["top_k"] = top_k

        self.client = ChatGoogleGenerativeAI(**client_kwargs)

    def chat(
            self,
            messages: List[ChatMessage],
            *,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            stream: bool = False,
            **kwargs: Any
    ) -> ChatMessage:
        """
        Send a chat request to the Gemini model.

        :param messages: List of ChatMessage objects
        :param temperature: Override sampling temperature
        :param max_tokens: Override max tokens
        :param stream: Whether to stream (handled separately)
        :param kwargs: Additional parameters
        """
        call_params: Dict[str, Any] = {}
        if temperature is not None:
            call_params["temperature"] = temperature
        if max_tokens is not None:
            call_params["max_output_tokens"] = max_tokens
        call_params.update(kwargs)

        lc_messages = LangChainConverter.to_lc(messages)
        response = self.client.invoke(lc_messages, **call_params)

        if hasattr(response, 'content') and isinstance(response.content, list):
            response.content = _extract_text_content(response.content)

        return LangChainConverter.from_lc_message(response)

    def stream(
            self,
            messages: List[ChatMessage],
            **call_params: Any,
    ) -> Iterator[Union[str, ChatMessage]]:
        """
        Provider-level streaming with ``thought_signature`` round-trip support.

        Gemini 2.5+ models embed an opaque ``thought_signature`` bytes field in
        every function-call Part when the thinking feature is active.  The
        Gemini API requires those bytes to be echoed verbatim in the following
        request; without them it returns:

            400 Function call is missing a thought_signature in functionCall parts

        ``langchain-google-genai`` silently drops the field during conversation-
        history conversion, so any multi-turn tool-use session fails on the
        second LLM call.

        This implementation bypasses LangChain's lossy conversion layer and
        calls ``GenerativeServiceClient.stream_generate_content`` directly so
        that:
          • On the way *out* — ``thought_signature`` bytes are captured for every
            function-call Part and stored in the returned
            ``ChatMessage.additional_kwargs["thought_signatures"]``.
          • On the way *in* — any stored bytes are injected back into the matching
            ``Content`` Parts of the ``GenerateContentRequest`` before the call.

        Yields ``str`` tokens for text responses, then (if tools were called) one
        ``ChatMessage`` with ``tool_calls`` set.
        """
        # Unwrap RunnableBinding → ChatGoogleGenerativeAI + bound tool list
        lc_model: ChatGoogleGenerativeAI
        if hasattr(self.client, "bound"):
            lc_model = self.client.bound
            bound_tools = self.client.kwargs.get("tools")
        else:
            lc_model = self.client  # type: ignore[assignment]
            bound_tools = None

        # Build GenerateContentRequest via LangChain's own _prepare_request
        lc_history = LangChainConverter.to_lc(messages)
        request = lc_model._prepare_request(lc_history, tools=bound_tools)

        # Inject stored thought_signatures from prior turns back into the request
        self._inject_thought_signatures(request, messages)

        # Stream directly from the underlying Gemini gRPC client
        raw_stream = _chat_with_retry(
            request=request,
            generation_method=lc_model.client.stream_generate_content,
            max_retries=getattr(lc_model, "max_retries", 6),
            metadata=getattr(lc_model, "default_metadata", ()),
        )

        accumulated_text = ""
        fc_parts: List[Dict[str, Any]] = []

        for chunk in raw_stream:
            for candidate in chunk.candidates:
                for part in candidate.content.parts:
                    if part.thought:
                        continue
                    if part.text:
                        accumulated_text += part.text
                        yield part.text
                    if part.function_call.name:
                        sig = bytes(part.thought_signature) if part.thought_signature else None
                        fc_parts.append({
                            "name": part.function_call.name,
                            "args": dict(part.function_call.args),
                            "sig": sig,
                        })

        if fc_parts:
            tool_calls = [
                ToolCall(
                    tool_call_id=str(uuid4()),
                    name=fc["name"],
                    args=fc["args"],
                )
                for fc in fc_parts
            ]
            signatures = [fc["sig"] for fc in fc_parts]
            yield ChatMessage(
                role=Role.ASSISTANT,
                content=accumulated_text,
                tool_calls=tool_calls,
                additional_kwargs={"thought_signatures": signatures},
            )

    @staticmethod
    def _inject_thought_signatures(request: Any, messages: List[ChatMessage]) -> None:
        """
        Scan the message history for assistant messages that carry stored
        ``thought_signatures`` and write them back into the matching
        FunctionCall Parts of the ``GenerateContentRequest``.
        """
        sig_queues: List[List[Optional[bytes]]] = []
        for msg in messages:
            if (
                msg.role == Role.ASSISTANT
                and msg.tool_calls
                and msg.additional_kwargs
                and msg.additional_kwargs.get("thought_signatures")
            ):
                sig_queues.append(list(msg.additional_kwargs["thought_signatures"]))

        if not sig_queues:
            return

        queue_idx = 0
        for content in request.contents:
            if queue_idx >= len(sig_queues):
                break
            fc_parts = [p for p in content.parts if p.function_call.name]
            if not fc_parts:
                continue
            sigs = sig_queues[queue_idx]
            for part, sig in zip(fc_parts, sigs):
                if sig:
                    part.thought_signature = sig
            queue_idx += 1

    def bind_tools(self, tools: List[BaseTool]) -> "GoogleGenAILLM":
        """
        Return a new GoogleGenAILLM instance with tools bound.

        Uses GoogleGenAIToolsConverter which sanitizes schemas to meet
        Google GenAI's strict validation requirements.
        """
        new_llm = copy.copy(self)
        new_llm.client = self.client.bind_tools(GoogleGenAIToolsConverter.to_lc(tools))
        return new_llm

    @property
    def name(self) -> str:
        return self._name

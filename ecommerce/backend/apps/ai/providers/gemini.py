import json
import re
import uuid
from collections.abc import Iterator
from typing import Any
from urllib import error, request

from django.conf import settings

from .base import (
    AIProviderError,
    BaseAIProvider,
    ChatChunk,
    EmbeddingResponse,
    ProviderResponse,
    ToolCall,
)

MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
RETRYABLE_HTTP_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}
RESPONSE_MIME_TYPES = {
    "application/json": "APPLICATION_JSON",
    "text/plain": "TEXT_PLAIN",
}


class GeminiProvider(BaseAIProvider):
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        generation_base_url: str | None = None,
        embedding_base_url: str | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self._generation_base_url = (
            generation_base_url or settings.GEMINI_GENERATION_BASE_URL
        ).rstrip("/")
        self._embedding_base_url = (
            embedding_base_url or settings.GEMINI_EMBEDDING_BASE_URL
        ).rstrip("/")

    def generate_text(
        self,
        *,
        prompt: str,
        system_prompt: str = "",
        model_name: str | None = None,
        timeout: float,
        response_mime_type: str | None = None,
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> ProviderResponse:
        model = self._validated_model(model_name or settings.AI_MODEL)
        generation_config: dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        }
        if model.startswith("gemini-3"):
            generation_config["thinkingConfig"] = {"thinkingLevel": "minimal"}
        if response_mime_type:
            text_format: dict[str, Any] = {
                "mimeType": RESPONSE_MIME_TYPES.get(
                    response_mime_type.lower(),
                    response_mime_type,
                )
            }
            if response_schema:
                text_format["schema"] = response_schema
            generation_config["responseFormat"] = {"text": text_format}

        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        data = self._post_json(
            f"{self._generation_base_url}/models/{model}:generateContent",
            payload,
            timeout=timeout,
        )
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError(
                "Gemini returned an invalid generation response",
                code="invalid_response",
                retryable=False,
            ) from exc
        if not text:
            raise AIProviderError(
                "Gemini returned an empty generation response",
                code="empty_response",
                retryable=False,
            )

        usage = data.get("usageMetadata") or {}
        return ProviderResponse(
            text=text,
            input_tokens=self._nonnegative_int(usage.get("promptTokenCount")),
            output_tokens=self._nonnegative_int(
                usage.get("candidatesTokenCount") or usage.get("responseTokenCount")
            ),
            metadata={
                "finish_reason": (data.get("candidates", [{}])[0].get("finishReason", "")),
                "total_tokens": self._nonnegative_int(usage.get("totalTokenCount")),
            },
        )

    def generate_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str = "",
        model_name: str | None = None,
        timeout: float,
        temperature: float = 0.3,
        max_output_tokens: int = 1024,
    ) -> Iterator[ChatChunk]:
        model = self._validated_model(model_name or settings.AI_MODEL)
        generation_config: dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        }
        if model.startswith("gemini-3"):
            generation_config["thinkingConfig"] = {"thinkingLevel": "minimal"}

        context_instructions = [
            str(message.get("content", "")).strip()
            for message in messages
            if message.get("role") == "system" and str(message.get("content", "")).strip()
        ]
        payload: dict[str, Any] = {
            "contents": self._chat_contents(messages),
            "generationConfig": generation_config,
        }
        if tools:
            payload["tools"] = [{"functionDeclarations": tools}]
        combined_instruction = "\n\n".join(
            part for part in (system_prompt, *context_instructions) if part
        )
        if combined_instruction:
            payload["systemInstruction"] = {"parts": [{"text": combined_instruction}]}

        url = f"{self._generation_base_url}/models/{model}:streamGenerateContent?alt=sse"
        for data in self._stream_json(url, payload, timeout=timeout):
            candidates = data.get("candidates") or []
            candidate = candidates[0] if candidates and isinstance(candidates[0], dict) else {}
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            delta_text = ""
            tool_calls: list[ToolCall] = []
            for part in parts:
                if not isinstance(part, dict):
                    continue
                if isinstance(part.get("text"), str) and not part.get("thought"):
                    delta_text += part["text"]
                function_call = part.get("functionCall")
                if not isinstance(function_call, dict):
                    continue
                name = str(function_call.get("name", "")).strip()
                arguments = function_call.get("args")
                if not name or not isinstance(arguments, dict):
                    continue
                tool_calls.append(
                    ToolCall(
                        id=str(function_call.get("id") or f"gemini-{uuid.uuid4().hex}"),
                        name=name,
                        arguments=arguments,
                        thought_signature=str(part.get("thoughtSignature", "")),
                    )
                )

            usage = data.get("usageMetadata") or {}
            finish_reason = candidate.get("finishReason")
            if delta_text or tool_calls or finish_reason:
                yield ChatChunk(
                    delta_text=delta_text,
                    tool_calls=tool_calls,
                    finish_reason=str(finish_reason) if finish_reason else None,
                    input_tokens=self._nonnegative_int(usage.get("promptTokenCount")),
                    output_tokens=self._nonnegative_int(
                        usage.get("candidatesTokenCount") or usage.get("responseTokenCount")
                    ),
                )

    @staticmethod
    def _chat_contents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        contents: list[dict[str, Any]] = []
        for message in messages:
            role = str(message.get("role", "user"))
            if role == "system":
                continue
            if role == "tool":
                raw_content = message.get("content", "")
                try:
                    result = (
                        json.loads(raw_content) if isinstance(raw_content, str) else raw_content
                    )
                except json.JSONDecodeError:
                    result = {"result": str(raw_content)}
                response: dict[str, Any] = {
                    "name": str(message.get("name", "")),
                    "response": result if isinstance(result, dict) else {"result": result},
                }
                if message.get("tool_call_id"):
                    response["id"] = str(message["tool_call_id"])
                contents.append({"role": "user", "parts": [{"functionResponse": response}]})
                continue

            parts: list[dict[str, Any]] = []
            content = str(message.get("content", ""))
            if content:
                parts.append({"text": content})
            for raw_call in message.get("tool_calls") or []:
                if not isinstance(raw_call, dict):
                    continue
                function_call: dict[str, Any] = {
                    "name": str(raw_call.get("name", "")),
                    "args": raw_call.get("arguments") or {},
                }
                if raw_call.get("id"):
                    function_call["id"] = str(raw_call["id"])
                part: dict[str, Any] = {"functionCall": function_call}
                if raw_call.get("thought_signature"):
                    part["thoughtSignature"] = str(raw_call["thought_signature"])
                parts.append(part)
            if parts:
                contents.append(
                    {"role": "model" if role == "assistant" else "user", "parts": parts}
                )
        return contents

    def embed_text(
        self,
        *,
        text: str,
        task_type: str,
        title: str = "",
        model_name: str | None = None,
        dimensions: int,
        timeout: float,
    ) -> EmbeddingResponse:
        model = self._validated_model(model_name or settings.AI_EMBEDDING_MODEL)
        normalized_task = task_type.strip().lower()
        if normalized_task in {"query", "retrieval_query", "search_query"}:
            provider_task = "RETRIEVAL_QUERY"
            content_text = f"task: search result | query: {text.strip()}"
        elif normalized_task in {
            "document",
            "retrieval_document",
            "search_document",
        }:
            provider_task = "RETRIEVAL_DOCUMENT"
            content_text = f"title: {title.strip()} | text: {text.strip()}"
        else:
            provider_task = "SEMANTIC_SIMILARITY"
            content_text = text.strip()

        embed_config: dict[str, Any] = {
            "outputDimensionality": dimensions,
        }
        payload: dict[str, Any] = {
            "model": f"models/{model}",
            "content": {"parts": [{"text": content_text}]},
            "embedContentConfig": embed_config,
        }
        # gemini-embedding-2 uses explicit content prefixes. The older
        # gemini-embedding-001 contract accepts taskType/title in config.
        if model.endswith("embedding-001"):
            embed_config["taskType"] = provider_task
            if title and provider_task == "RETRIEVAL_DOCUMENT":
                embed_config["title"] = title.strip()

        data = self._post_json(
            f"{self._embedding_base_url}/models/{model}:embedContent",
            payload,
            timeout=timeout,
        )
        try:
            values = data["embedding"]["values"]
            vector = [float(value) for value in values]
        except (KeyError, TypeError, ValueError) as exc:
            raise AIProviderError(
                "Gemini returned an invalid embedding response",
                code="invalid_response",
                retryable=False,
            ) from exc
        if len(vector) != dimensions:
            raise AIProviderError(
                "Gemini returned an embedding with an unexpected dimension",
                code="invalid_dimensions",
                retryable=False,
            )

        usage = data.get("usageMetadata") or {}
        return EmbeddingResponse(
            vector=vector,
            input_tokens=self._nonnegative_int(
                usage.get("promptTokenCount") or usage.get("inputTokenCount")
            ),
            metadata={"task_type": provider_task},
        )

    def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        timeout: float,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise AIProviderError(
                "Gemini provider is not configured",
                code="provider_not_configured",
                retryable=False,
            )

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self._api_key,
            },
        )
        try:
            with request.urlopen(http_request, timeout=timeout) as response:
                response_body = response.read()
        except error.HTTPError as exc:
            raise AIProviderError(
                f"Gemini HTTP request failed with status {exc.code}",
                code=f"http_{exc.code}",
                retryable=exc.code in RETRYABLE_HTTP_STATUSES,
            ) from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise AIProviderError(
                "Gemini request could not reach the provider",
                code="network_error",
                retryable=True,
            ) from exc

        try:
            decoded = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AIProviderError(
                "Gemini returned malformed JSON",
                code="invalid_json",
                retryable=False,
            ) from exc
        if not isinstance(decoded, dict):
            raise AIProviderError(
                "Gemini returned an unexpected response",
                code="invalid_response",
                retryable=False,
            )
        return decoded

    def _stream_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        timeout: float,
    ) -> Iterator[dict[str, Any]]:
        if not self._api_key:
            raise AIProviderError(
                "Gemini provider is not configured",
                code="provider_not_configured",
                retryable=False,
            )

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Accept": "text/event-stream",
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self._api_key,
            },
        )
        try:
            with request.urlopen(http_request, timeout=timeout) as response:
                data_lines: list[str] = []
                for raw_line in response:
                    try:
                        line = raw_line.decode("utf-8").rstrip("\r\n")
                    except UnicodeDecodeError as exc:
                        raise AIProviderError(
                            "Gemini returned malformed streaming data",
                            code="invalid_stream",
                            retryable=False,
                        ) from exc
                    if not line:
                        if data_lines:
                            yield self._decode_sse_data("\n".join(data_lines))
                            data_lines = []
                        continue
                    if line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        data_lines.append(line[5:].lstrip())
                if data_lines:
                    yield self._decode_sse_data("\n".join(data_lines))
        except error.HTTPError as exc:
            raise AIProviderError(
                f"Gemini HTTP request failed with status {exc.code}",
                code=f"http_{exc.code}",
                retryable=exc.code in RETRYABLE_HTTP_STATUSES,
            ) from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise AIProviderError(
                "Gemini request could not reach the provider",
                code="network_error",
                retryable=True,
            ) from exc

    @staticmethod
    def _decode_sse_data(value: str) -> dict[str, Any]:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise AIProviderError(
                "Gemini returned malformed streaming JSON",
                code="invalid_json",
                retryable=False,
            ) from exc
        if not isinstance(decoded, dict):
            raise AIProviderError(
                "Gemini returned an unexpected streaming response",
                code="invalid_response",
                retryable=False,
            )
        return decoded

    @staticmethod
    def _validated_model(model_name: str) -> str:
        normalized = model_name.strip()
        if not MODEL_NAME_PATTERN.fullmatch(normalized):
            raise AIProviderError(
                "Invalid Gemini model name",
                code="invalid_model",
                retryable=False,
            )
        return normalized

    @staticmethod
    def _nonnegative_int(value: Any) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

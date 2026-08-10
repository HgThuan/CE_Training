import json
import re
from typing import Any
from urllib import error, request

from django.conf import settings

from .base import (
    AIProviderError,
    BaseAIProvider,
    EmbeddingResponse,
    ProviderResponse,
)

MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
RETRYABLE_HTTP_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}


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
        if response_mime_type:
            text_format: dict[str, Any] = {"mimeType": response_mime_type}
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

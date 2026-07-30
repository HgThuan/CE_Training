import json
import logging
import math
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from django.conf import settings

from apps.common.cache_utils import build_cache_key, safe_cache_get, safe_cache_set

from .models import (
    EMBEDDING_DIMENSIONS,
    AIRequestLog,
    sanitize_ai_text,
)
from .providers import (
    AIProviderError,
    BaseAIProvider,
    EmbeddingResponse,
    GeminiProvider,
    ProviderResponse,
)

logger = logging.getLogger(__name__)

AI_CACHE_PAYLOAD_VERSION = 1
JSON_CODE_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*(.*?)\s*```\s*$",
    re.IGNORECASE | re.DOTALL,
)
WORD_RE = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)
PRICE_MAX_RE = re.compile(
    r"\b(?:dưới|không quá|tối đa)\s+(\d+(?:[.,]\d+)?)\s*(triệu|tr|k|nghìn)?\b",
    re.IGNORECASE,
)
PRICE_MIN_RE = re.compile(
    r"\b(?:trên|từ|ít nhất|tối thiểu)\s+(\d+(?:[.,]\d+)?)\s*(triệu|tr|k|nghìn)?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class AIResult:
    text: str
    ai_used: bool
    fallback_used: bool
    cached: bool
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vector: list[float]
    ai_used: bool
    fallback_used: bool
    cached: bool
    model_name: str
    input_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class AIService:
    """The only application service allowed to call an external AI provider."""

    SUPPORTED_PROVIDERS: dict[str, type[BaseAIProvider]] = {
        "gemini": GeminiProvider,
    }

    def __init__(
        self,
        *,
        provider: BaseAIProvider | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        monotonic_fn: Callable[[], float] | None = None,
    ) -> None:
        self._provider = provider
        self._sleep = sleep_fn or time.sleep
        self._monotonic = monotonic_fn or time.monotonic

    @classmethod
    def is_configured(cls) -> bool:
        if not settings.AI_FEATURES_ENABLED:
            return False
        provider_name = str(settings.AI_PROVIDER).strip().lower()
        if provider_name == "gemini":
            return bool(str(settings.GEMINI_API_KEY).strip())
        return False

    def generate_text(
        self,
        *,
        feature: str,
        prompt: str,
        system_prompt: str = "",
        user: Any = None,
        fallback: str | Callable[[], str] | None = None,
        cache_ttl: int | None = None,
        cache_context: Mapping[str, Any] | None = None,
        model_name: str | None = None,
        prompt_template_version: str = "",
        response_mime_type: str | None = None,
        response_schema: Mapping[str, Any] | None = None,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
    ) -> AIResult:
        selected_model = model_name or settings.AI_MODEL
        provider_name = self._provider_name
        started_at = self._monotonic()

        if not settings.AI_FEATURES_ENABLED:
            result = AIResult(
                text=self._resolve_text_fallback(fallback),
                ai_used=False,
                fallback_used=True,
                cached=False,
                model_name=selected_model,
                metadata={"error_code": "feature_disabled"},
            )
            self._write_log(
                feature=feature,
                provider=provider_name,
                model_name=selected_model,
                prompt=prompt,
                response=result.text,
                status=AIRequestLog.Status.FALLBACK,
                latency_ms=self._elapsed_ms(started_at),
                user=user,
                prompt_template_version=prompt_template_version,
                error_code="feature_disabled",
                error_message="AI features are disabled",
                metadata={"cache_hit": False, "attempts": 0},
            )
            return result

        cache_timeout = (
            settings.AI_CACHE_TTL_SECONDS if cache_ttl is None else max(0, int(cache_ttl))
        )
        cache_key = self._cache_key(
            "text",
            {
                "feature": feature,
                "model": selected_model,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "response_mime_type": response_mime_type or "",
                "response_schema": response_schema or {},
                "temperature": temperature,
                "max_output_tokens": (max_output_tokens or settings.AI_MAX_OUTPUT_TOKENS),
                "context": dict(cache_context or {}),
            },
        )
        if cache_timeout:
            cached = safe_cache_get(cache_key)
            cached_result = self._text_result_from_cache(
                cached,
                model_name=selected_model,
            )
            if cached_result is not None:
                self._write_log(
                    feature=feature,
                    provider=provider_name,
                    model_name=selected_model,
                    prompt=prompt,
                    response=cached_result.text,
                    status=AIRequestLog.Status.CACHED,
                    latency_ms=self._elapsed_ms(started_at),
                    user=user,
                    prompt_template_version=prompt_template_version,
                    metadata={"cache_hit": True, "attempts": 0},
                )
                return cached_result

        try:
            response, attempts = self._call_with_retry(
                lambda: self.provider.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model_name=selected_model,
                    timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
                    response_mime_type=response_mime_type,
                    response_schema=dict(response_schema or {}) if response_schema else None,
                    temperature=temperature,
                    max_output_tokens=(max_output_tokens or settings.AI_MAX_OUTPUT_TOKENS),
                )
            )
            if not isinstance(response, ProviderResponse):
                raise AIProviderError(
                    "Provider returned an invalid text response",
                    code="invalid_response",
                    retryable=False,
                )
        except Exception as exc:
            error_code = self._error_code(exc)
            result = AIResult(
                text=self._resolve_text_fallback(fallback),
                ai_used=False,
                fallback_used=True,
                cached=False,
                model_name=selected_model,
                metadata={"error_code": error_code},
            )
            self._write_log(
                feature=feature,
                provider=provider_name,
                model_name=selected_model,
                prompt=prompt,
                response=result.text,
                status=AIRequestLog.Status.FALLBACK,
                latency_ms=self._elapsed_ms(started_at),
                user=user,
                prompt_template_version=prompt_template_version,
                error_code=error_code,
                error_message=str(exc),
                metadata={
                    "cache_hit": False,
                    "attempts": getattr(exc, "_ai_attempts", 0),
                },
            )
            return result

        result = AIResult(
            text=response.text,
            ai_used=True,
            fallback_used=False,
            cached=False,
            model_name=selected_model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            metadata=response.metadata,
        )
        if cache_timeout:
            safe_cache_set(
                cache_key,
                {
                    "version": AI_CACHE_PAYLOAD_VERSION,
                    "kind": "text",
                    **asdict(result),
                },
                timeout=cache_timeout,
            )
        self._write_log(
            feature=feature,
            provider=provider_name,
            model_name=selected_model,
            prompt=prompt,
            response=response.text,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            status=AIRequestLog.Status.SUCCESS,
            latency_ms=self._elapsed_ms(started_at),
            user=user,
            prompt_template_version=prompt_template_version,
            metadata={
                "cache_hit": False,
                "attempts": attempts,
                **response.metadata,
            },
        )
        return result

    def get_embedding(
        self,
        *,
        feature: str,
        text: str,
        task_type: str,
        title: str = "",
        user: Any = None,
        fallback: list[float] | Callable[[], list[float]] | None = None,
        model_name: str | None = None,
        cache_ttl: int | None = None,
    ) -> EmbeddingResult:
        selected_model = model_name or settings.AI_EMBEDDING_MODEL
        provider_name = self._provider_name
        started_at = self._monotonic()
        if not settings.AI_FEATURES_ENABLED:
            return self._embedding_fallback(
                feature=feature,
                text=text,
                task_type=task_type,
                title=title,
                user=user,
                fallback=fallback,
                selected_model=selected_model,
                provider_name=provider_name,
                started_at=started_at,
                error_code="feature_disabled",
                error_message="AI features are disabled",
                attempts=0,
            )

        cache_timeout = (
            settings.AI_EMBEDDING_CACHE_TTL_SECONDS if cache_ttl is None else max(0, int(cache_ttl))
        )
        cache_key = self._cache_key(
            "embedding",
            {
                "feature": feature,
                "model": selected_model,
                "dimensions": EMBEDDING_DIMENSIONS,
                "task_type": task_type,
                "title": title,
                "text": text,
            },
        )
        if cache_timeout:
            cached = safe_cache_get(cache_key)
            cached_result = self._embedding_result_from_cache(
                cached,
                model_name=selected_model,
            )
            if cached_result is not None:
                self._write_log(
                    feature=feature,
                    provider=provider_name,
                    model_name=selected_model,
                    prompt=text,
                    status=AIRequestLog.Status.CACHED,
                    latency_ms=self._elapsed_ms(started_at),
                    user=user,
                    metadata={
                        "cache_hit": True,
                        "attempts": 0,
                        "task_type": task_type,
                    },
                )
                return cached_result

        if settings.AI_EMBEDDING_DIMENSIONS != EMBEDDING_DIMENSIONS:
            return self._embedding_fallback(
                feature=feature,
                text=text,
                task_type=task_type,
                title=title,
                user=user,
                fallback=fallback,
                selected_model=selected_model,
                provider_name=provider_name,
                started_at=started_at,
                error_code="invalid_dimensions",
                error_message=("AI_EMBEDDING_DIMENSIONS must match the database vector schema"),
                attempts=0,
            )

        try:
            response, attempts = self._call_with_retry(
                lambda: self.provider.embed_text(
                    text=text,
                    task_type=task_type,
                    title=title,
                    model_name=selected_model,
                    dimensions=EMBEDDING_DIMENSIONS,
                    timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
                )
            )
            if not isinstance(response, EmbeddingResponse):
                raise AIProviderError(
                    "Provider returned an invalid embedding response",
                    code="invalid_response",
                    retryable=False,
                )
            if len(response.vector) != EMBEDDING_DIMENSIONS:
                raise AIProviderError(
                    "Provider returned an embedding with an unexpected dimension",
                    code="invalid_dimensions",
                    retryable=False,
                )
        except Exception as exc:
            return self._embedding_fallback(
                feature=feature,
                text=text,
                task_type=task_type,
                title=title,
                user=user,
                fallback=fallback,
                selected_model=selected_model,
                provider_name=provider_name,
                started_at=started_at,
                error_code=self._error_code(exc),
                error_message=str(exc),
                attempts=getattr(exc, "_ai_attempts", 0),
            )

        result = EmbeddingResult(
            vector=response.vector,
            ai_used=True,
            fallback_used=False,
            cached=False,
            model_name=selected_model,
            input_tokens=response.input_tokens,
            metadata=response.metadata,
        )
        if cache_timeout:
            safe_cache_set(
                cache_key,
                {
                    "version": AI_CACHE_PAYLOAD_VERSION,
                    "kind": "embedding",
                    **asdict(result),
                },
                timeout=cache_timeout,
            )
        self._write_log(
            feature=feature,
            provider=provider_name,
            model_name=selected_model,
            prompt=self._embedding_log_prompt(
                text=text,
                task_type=task_type,
                title=title,
            ),
            input_tokens=response.input_tokens,
            status=AIRequestLog.Status.SUCCESS,
            latency_ms=self._elapsed_ms(started_at),
            user=user,
            metadata={
                "cache_hit": False,
                "attempts": attempts,
                "task_type": task_type,
                **response.metadata,
            },
        )
        return result

    def extract_search_intent(
        self,
        query: str,
        *,
        user: Any = None,
    ) -> dict[str, Any]:
        normalized_query = query.strip()
        fallback = self._fallback_search_intent(normalized_query)
        prompt = (
            "Extract ecommerce search intent from the query below. "
            "Return only JSON with keys: keywords (array of strings), filters "
            "(object using only price_min, price_max, "
            "rating_min, in_stock), and explanation (short string).\n"
            "Rules:\n"
            "1. Keywords must contain the core product names, features, categories, and brands. Do NOT include price words in keywords if mapped to filters.\n"
            "2. For price filters, ALWAYS convert to pure numbers in VND (e.g. '10 triệu' -> 10000000, '50k' -> 50000).\n"
            f"Query: {normalized_query}"
        )
        result = self.generate_text(
            feature=AIRequestLog.Feature.SMART_SEARCH,
            prompt=prompt,
            system_prompt=(
                "You parse Vietnamese ecommerce queries into strict structured data. "
                "Never invent filters that are not explicit in the query. "
                "Prices must be converted to exact VND integer values. "
                "Do NOT extract categories or brands as filters; leave them in keywords."
            ),
            user=user,
            fallback="",
            cache_context={"query": normalized_query},
            prompt_template_version="smart-search-v8",
            response_mime_type="application/json",
            temperature=0,
            max_output_tokens=8192,
        )
        if not result.ai_used:
            return fallback
        parsed = self._parse_json_object(result.text)
        if parsed is None:
            return fallback

        keywords = parsed.get("keywords")
        if not isinstance(keywords, list):
            return fallback
        normalized_keywords = []
        for keyword in keywords[:12]:
            if not isinstance(keyword, str):
                continue
            normalized_keyword = keyword.strip()[:100]
            if normalized_keyword:
                normalized_keywords.append(normalized_keyword)
        # We allow normalized_keywords to be empty if all terms were mapped to filters.

        raw_filters = parsed.get("filters")
        filters = self._normalize_search_filters(
            raw_filters if isinstance(raw_filters, dict) else {}
        )
        explanation = sanitize_ai_text(
            parsed.get("explanation", ""),
            max_length=300,
        )
        return {
            "keywords": normalized_keywords,
            "filters": filters,
            "explanation": explanation,
            "ai_used": True,
            "fallback_used": False,
        }

    @property
    def provider(self) -> BaseAIProvider:
        if self._provider is None:
            provider_class = self.SUPPORTED_PROVIDERS.get(self._provider_name)
            if provider_class is None:
                raise AIProviderError(
                    "Configured AI provider is not supported",
                    code="unsupported_provider",
                    retryable=False,
                )
            self._provider = provider_class()
        return self._provider

    @property
    def _provider_name(self) -> str:
        if self._provider is not None:
            return str(self._provider.name).strip().lower()
        return str(settings.AI_PROVIDER).strip().lower()

    def _call_with_retry(
        self,
        operation: Callable[[], ProviderResponse | EmbeddingResponse],
    ) -> tuple[ProviderResponse | EmbeddingResponse, int]:
        max_attempts = max(1, int(settings.AI_MAX_RETRIES) + 1)
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return operation(), attempt
            except Exception as exc:
                last_error = exc
                retryable = (isinstance(exc, AIProviderError) and exc.retryable) or isinstance(
                    exc, (TimeoutError, OSError)
                )
                if not retryable or attempt >= max_attempts:
                    try:
                        exc.__dict__["_ai_attempts"] = attempt
                    except Exception:
                        pass
                    raise
                delay = float(settings.AI_RETRY_BACKOFF_SECONDS) * (2 ** (attempt - 1))
                self._sleep(delay)
        if last_error is not None:
            raise last_error
        raise AIProviderError("AI provider call did not run")

    def _embedding_fallback(
        self,
        *,
        feature: str,
        text: str,
        task_type: str,
        title: str,
        user: Any,
        fallback: list[float] | Callable[[], list[float]] | None,
        selected_model: str,
        provider_name: str,
        started_at: float,
        error_code: str,
        error_message: str,
        attempts: int,
    ) -> EmbeddingResult:
        vector = self._resolve_embedding_fallback(fallback)
        result = EmbeddingResult(
            vector=vector,
            ai_used=False,
            fallback_used=True,
            cached=False,
            model_name=selected_model,
            metadata={"error_code": error_code},
        )
        self._write_log(
            feature=feature,
            provider=provider_name,
            model_name=selected_model,
            prompt=self._embedding_log_prompt(
                text=text,
                task_type=task_type,
                title=title,
            ),
            status=AIRequestLog.Status.FALLBACK,
            latency_ms=self._elapsed_ms(started_at),
            user=user,
            error_code=error_code,
            error_message=error_message,
            metadata={
                "cache_hit": False,
                "attempts": attempts,
                "task_type": task_type,
            },
        )
        return result

    def _write_log(
        self,
        *,
        feature: str,
        provider: str,
        model_name: str,
        status: str,
        latency_ms: int,
        prompt: str = "",
        response: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        user: Any = None,
        prompt_template_version: str = "",
        error_code: str = "",
        error_message: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        try:
            AIRequestLog.objects.create(
                user=self._persisted_user(user),
                feature=feature,
                provider=provider,
                model_name=model_name,
                prompt_template_version=prompt_template_version,
                prompt=prompt,
                response=response,
                input_tokens=max(0, int(input_tokens)),
                output_tokens=max(0, int(output_tokens)),
                estimated_cost=self._estimated_cost(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                ),
                latency_ms=max(0, latency_ms),
                status=status,
                error_code=error_code,
                error_message=error_message,
                metadata=dict(metadata or {}),
            )
        except Exception:
            logger.warning(
                "Could not persist AI request log",
                extra={"ai_feature": feature, "ai_status": status},
                exc_info=True,
            )

    @staticmethod
    def _persisted_user(user: Any) -> Any:
        if (
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "pk", None)
        ):
            return user
        return None

    @staticmethod
    def _estimated_cost(*, input_tokens: int, output_tokens: int) -> Decimal:
        million = Decimal("1000000")
        input_rate = Decimal(str(settings.AI_INPUT_COST_PER_MILLION))
        output_rate = Decimal(str(settings.AI_OUTPUT_COST_PER_MILLION))
        return (
            Decimal(max(0, int(input_tokens))) * input_rate / million
            + Decimal(max(0, int(output_tokens))) * output_rate / million
        )

    @staticmethod
    def _cache_key(kind: str, payload: Mapping[str, Any]) -> str:
        return build_cache_key(f"ai:{kind}", payload)

    @staticmethod
    def _text_result_from_cache(
        cached: Any,
        *,
        model_name: str,
    ) -> AIResult | None:
        if not isinstance(cached, dict):
            return None
        if (
            cached.get("version") != AI_CACHE_PAYLOAD_VERSION
            or cached.get("kind") != "text"
            or cached.get("model_name") != model_name
            or not isinstance(cached.get("text"), str)
        ):
            return None
        try:
            input_tokens = max(0, int(cached.get("input_tokens", 0)))
            output_tokens = max(0, int(cached.get("output_tokens", 0)))
        except (TypeError, ValueError, OverflowError):
            return None
        metadata = cached.get("metadata")
        if not isinstance(metadata, dict):
            return None
        return AIResult(
            text=cached["text"],
            ai_used=True,
            fallback_used=False,
            cached=True,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata=dict(metadata),
        )

    @staticmethod
    def _embedding_result_from_cache(
        cached: Any,
        *,
        model_name: str,
    ) -> EmbeddingResult | None:
        if not isinstance(cached, dict):
            return None
        vector = cached.get("vector")
        if (
            cached.get("version") != AI_CACHE_PAYLOAD_VERSION
            or cached.get("kind") != "embedding"
            or cached.get("model_name") != model_name
            or not isinstance(vector, list)
            or len(vector) != EMBEDDING_DIMENSIONS
        ):
            return None
        try:
            normalized_vector = [float(value) for value in vector]
        except (TypeError, ValueError):
            return None
        try:
            input_tokens = max(0, int(cached.get("input_tokens", 0)))
        except (TypeError, ValueError, OverflowError):
            return None
        metadata = cached.get("metadata")
        if not isinstance(metadata, dict):
            return None
        return EmbeddingResult(
            vector=normalized_vector,
            ai_used=True,
            fallback_used=False,
            cached=True,
            model_name=model_name,
            input_tokens=input_tokens,
            metadata=dict(metadata),
        )

    @staticmethod
    def _resolve_text_fallback(
        fallback: str | Callable[[], str] | None,
    ) -> str:
        try:
            value = fallback() if callable(fallback) else fallback
        except Exception:
            logger.warning("AI text fallback failed", exc_info=True)
            return ""
        return str(value) if value is not None else ""

    @staticmethod
    def _resolve_embedding_fallback(
        fallback: list[float] | Callable[[], list[float]] | None,
    ) -> list[float]:
        try:
            value = fallback() if callable(fallback) else fallback
            if not value:
                return []
            vector = [float(item) for item in value]
        except Exception:
            logger.warning("AI embedding fallback failed", exc_info=True)
            return []
        return vector if len(vector) == EMBEDDING_DIMENSIONS else []

    def _elapsed_ms(self, started_at: float) -> int:
        return max(0, int((self._monotonic() - started_at) * 1_000))

    @staticmethod
    def _error_code(exc: Exception) -> str:
        if isinstance(exc, AIProviderError):
            return exc.code
        if isinstance(exc, TimeoutError):
            return "timeout"
        return "provider_error"

    @staticmethod
    def _embedding_log_prompt(
        *,
        text: str,
        task_type: str,
        title: str,
    ) -> str:
        normalized_task = task_type.strip().lower()
        if normalized_task in {"query", "retrieval_query", "search_query"}:
            return f"task: search result | query: {text.strip()}"
        if normalized_task in {
            "document",
            "retrieval_document",
            "search_document",
        }:
            return f"title: {title.strip()} | text: {text.strip()}"
        return text.strip()

    @classmethod
    def _fallback_search_intent(cls, query: str) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        for pattern, key in (
            (PRICE_MAX_RE, "price_max"),
            (PRICE_MIN_RE, "price_min"),
        ):
            match = pattern.search(query)
            if match:
                filters[key] = cls._price_to_number(
                    match.group(1),
                    match.group(2) or "",
                )
        keywords = [
            word for word in WORD_RE.findall(query) if len(word) > 1 and not word.isdigit()
        ][:12]
        return {
            "keywords": keywords or ([query] if query else []),
            "filters": filters,
            "explanation": "",
            "ai_used": False,
            "fallback_used": True,
        }

    @staticmethod
    def _price_to_number(number: str, unit: str) -> int:
        value = Decimal(number.replace(",", "."))
        normalized_unit = unit.casefold()
        if normalized_unit in {"triệu", "tr"}:
            value *= Decimal("1000000")
        elif normalized_unit in {"k", "nghìn"}:
            value *= Decimal("1000")
        return max(0, int(value))

    @staticmethod
    def _parse_json_object(value: str) -> dict[str, Any] | None:
        match = JSON_CODE_FENCE_RE.match(value)
        candidate = match.group(1) if match else value
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _normalize_search_filters(filters: Mapping[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key in ("category", "brand", "shop"):
            value = filters.get(key)
            if isinstance(value, str) and value.strip():
                result[key] = value.strip()[:280]
        for key in ("price_min", "price_max", "rating_min"):
            value = filters.get(key)
            if isinstance(value, bool):
                continue
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError):
                continue
            if math.isfinite(number) and number >= 0:
                result[key] = int(number) if number.is_integer() else number
        in_stock = filters.get("in_stock")
        if isinstance(in_stock, bool):
            result["in_stock"] = in_stock
        return result

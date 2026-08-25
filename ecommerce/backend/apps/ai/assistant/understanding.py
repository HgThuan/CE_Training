from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import replace
from typing import Any

from apps.ai.models import AIRequestLog, sanitize_ai_payload, sanitize_ai_text
from apps.ai.product_matching import extract_price_filters
from apps.ai.services import AIService
from apps.catalog.models import Brand, Category
from apps.product.models import Attribute, AttributeValue
from apps.product.selectors import ProductSelector

from .discovery import match_discovery_scenario
from .prompts import (
    UNDERSTANDING_PROMPT_VERSION,
    UNDERSTANDING_RESPONSE_SCHEMA,
    UNDERSTANDING_SYSTEM_PROMPT,
)
from .schemas import ALLOWED_TASKS, AssistantIntent, QueryUnderstanding
from .slots import NO_PREFERENCE, extract_no_preferences, slot_aliases
from .state import ConversationState

MAX_VOCABULARY_ITEMS = 80
SECURITY_PATTERNS = (
    "ignore previous",
    "ignore all previous",
    "bo qua huong dan",
    "system prompt",
    "developer message",
    "show all user",
    "tat ca email",
    "raw sql",
    "database password",
    "access token",
    "refresh token",
)


class QueryUnderstandingService:
    def __init__(self, *, ai_service: AIService | None = None) -> None:
        self._ai_service = ai_service or AIService()

    def understand(
        self,
        *,
        text: str,
        state: ConversationState,
        user: Any,
    ) -> QueryUnderstanding:
        normalized_text = sanitize_ai_text(text, max_length=1_000).strip()
        vocabulary = self._catalog_vocabulary()
        deterministic = self._deterministic(
            normalized_text,
            vocabulary=vocabulary,
            state=state,
        )
        deterministic = self._inherit_conversation_intent(
            deterministic,
            state=state,
        )
        if deterministic.security_refusal:
            return deterministic
        if (
            deterministic.primary_intent
            in {
                AssistantIntent.ORDER_STATUS,
                AssistantIntent.RETURN_SUPPORT,
                AssistantIntent.PAYMENT_SUPPORT,
                AssistantIntent.PROMOTION,
                AssistantIntent.POLICY,
                AssistantIntent.HUMAN_HANDOFF,
            }
            and len(deterministic.tasks) == 1
        ):
            return deterministic

        prompt = self._prompt(
            text=normalized_text,
            state=state,
            vocabulary=vocabulary,
        )
        result = self._ai_service.generate_text(
            feature=AIRequestLog.Feature.OTHER,
            prompt=prompt,
            system_prompt=UNDERSTANDING_SYSTEM_PROMPT,
            user=user,
            fallback="",
            cache_ttl=0,
            prompt_template_version=UNDERSTANDING_PROMPT_VERSION,
            response_mime_type="application/json",
            response_schema=UNDERSTANDING_RESPONSE_SCHEMA,
            temperature=0,
            max_output_tokens=1_200,
        )
        if not result.ai_used:
            return deterministic
        parsed = self._parse_object(result.text)
        if parsed is None:
            return deterministic
        model_output = self._validated_model_output(parsed, vocabulary=vocabulary)
        return self._merge(deterministic, model_output)

    @classmethod
    def _deterministic(
        cls,
        text: str,
        *,
        vocabulary: dict[str, list[dict[str, str]]],
        state: ConversationState,
    ) -> QueryUnderstanding:
        normalized = _normalize(text)
        if any(pattern in normalized for pattern in SECURITY_PATTERNS):
            return QueryUnderstanding(
                primary_intent=AssistantIntent.SECURITY_REFUSAL,
                goals=("protect_private_data",),
                confidence=1.0,
                security_refusal=True,
            )

        entities: dict[str, Any] = {}
        constraints: dict[str, Any] = {"in_stock": True}
        preferences: dict[str, Any] = {}
        exclusions: dict[str, Any] = {}
        facts: dict[str, Any] = {}
        inferences: dict[str, Any] = {}
        goals: list[str] = []
        tasks: list[str] = []
        product_type = ""

        for item in vocabulary["categories"]:
            if _contains_term(normalized, item["normalized"]):
                entities["category"] = item["value"]
                break
        for item in vocabulary["brands"]:
            if _contains_term(normalized, item["normalized"]):
                entities["brand"] = item["value"]
                break

        raw_prices = extract_price_filters(text)
        prices = {
            {"min_price": "price_min", "max_price": "price_max"}.get(key, key): value
            for key, value in raw_prices.items()
        }
        constraints.update(prices)
        no_preferences = extract_no_preferences(
            text,
            pending_slots=state.pending_slots,
        )
        constraints.update(no_preferences)
        if no_preferences.get("budget") == NO_PREFERENCE:
            constraints.pop("price_min", None)
            constraints.pop("price_max", None)

        recipient = _extract_first(
            normalized,
            {
                "ban gai": "bạn gái",
                "ban trai": "bạn trai",
                "nguoi yeu": "người yêu",
                "me": "mẹ",
                "bo": "bố",
                "dong nghiep": "đồng nghiệp",
                "ban than": "bạn thân",
            },
        )
        occasion = _extract_first(
            normalized,
            {
                "sinh nhat": "sinh nhật",
                "tan gia": "tân gia",
                "tot nghiep": "tốt nghiệp",
                "ky niem": "kỷ niệm",
                "dam cuoi": "đám cưới",
                "giang sinh": "Giáng sinh",
            },
        )
        if recipient:
            facts["recipient"] = recipient
        if occasion:
            facts["occasion"] = occasion

        usage_match = re.search(
            r"\b(?:để|dùng cho|phục vụ|khi)\s+(.+?)(?=\s+(?:dưới|trên|tầm|khoảng)\b|[,.;]|$)",
            text,
            re.IGNORECASE,
        )
        if usage_match:
            preferences["usage"] = " ".join(usage_match.group(1).split())[:120]
        scenario = match_discovery_scenario(text)
        if scenario:
            preferences["usage"] = scenario.label

        interest = _extract_first(
            normalized,
            {
                "do cong nghe": "đồ công nghệ",
                "thoi trang": "thời trang",
                "lam dep": "làm đẹp",
                "my pham": "mỹ phẩm",
                "trang suc": "trang sức",
                "am thanh": "âm thanh",
            },
        )
        if interest:
            preferences["interest"] = interest
        priority = _extract_first(
            normalized,
            {
                "camera": "camera",
                "pin": "thời lượng pin",
                "hieu nang": "hiệu năng",
                "mong nhe": "mỏng nhẹ",
                "do ben": "độ bền",
            },
        )
        if priority:
            preferences["priority"] = priority

        if any(phrase in normalized for phrase in ("khong co may", "khong co thiet bi")):
            equipment = re.search(r"không\s+có\s+(.+?)(?=[,.;]|$)", text, re.IGNORECASE)
            if equipment:
                facts["unavailable_equipment"] = [equipment.group(1).strip()[:100]]

        if any(term in normalized for term in ("don hang", "don cua toi", "giao toi dau")):
            primary = AssistantIntent.ORDER_STATUS
            goals.append("track_order")
            tasks.append("get_order_status")
        elif any(term in normalized for term in ("doi tra", "tra hang", "hoan tien")):
            primary = AssistantIntent.RETURN_SUPPORT
            goals.append("resolve_return_question")
            tasks.append(
                "get_policy"
                if any(x in normalized for x in ("chinh sach", "dieu kien"))
                else "get_return_support"
            )
        elif any(term in normalized for term in ("thanh toan", "giao dich", "vnpay")):
            primary = AssistantIntent.PAYMENT_SUPPORT
            goals.append("resolve_payment_question")
            tasks.append(
                "get_policy"
                if any(x in normalized for x in ("chinh sach", "phuong thuc"))
                else "get_payment_support"
            )
        elif any(
            term in normalized for term in ("flash sale", "flashsale", "deal soc", "gio vang")
        ):
            primary = AssistantIntent.PROMOTION
            goals.append("check_flash_sale")
            tasks.append("get_flash_sales")
        elif any(term in normalized for term in ("voucher", "ma giam gia", "khuyen mai")):
            primary = AssistantIntent.PROMOTION
            goals.append("find_promotions")
            tasks.append("get_promotions")
        elif any(term in normalized for term in ("chinh sach", "bao hanh", "phi ship")):
            primary = AssistantIntent.POLICY
            goals.append("understand_policy")
            tasks.append("get_policy")
        elif any(term in normalized for term in ("gap nhan vien", "nhan vien ho tro", "cskh")):
            primary = AssistantIntent.HUMAN_HANDOFF
            goals.append("contact_human_support")
            tasks.append("human_handoff")
        elif "so sanh" in normalized:
            primary = AssistantIntent.PRODUCT_COMPARE
            goals.extend(("find_products", "compare_products"))
            tasks.extend(("search_products", "compare_products"))
        else:
            recommendation_terms = (
                "tu van",
                "goi y",
                "nen mua",
                "phu hop",
                "mua qua",
                "khong biet",
            )
            is_recommendation = any(term in normalized for term in recommendation_terms)
            primary = (
                AssistantIntent.PRODUCT_RECOMMENDATION
                if is_recommendation
                else AssistantIntent.PRODUCT_SEARCH
            )
            goals.append("recommend_products" if is_recommendation else "find_products")
            tasks.append("recommend_products" if is_recommendation else "search_products")

        product_signal = bool(
            entities.get("category")
            or entities.get("brand")
            or any(term in normalized for term in ("tim", "mua", "goi y", "tu van"))
        )
        if product_signal and primary not in {
            AssistantIntent.PRODUCT_SEARCH,
            AssistantIntent.PRODUCT_RECOMMENDATION,
            AssistantIntent.PRODUCT_COMPARE,
        }:
            goals.append("find_products")
            tasks.append("search_products")
        secondary_routes = (
            (("don hang", "don cua toi", "giao toi dau"), "track_order", "get_order_status"),
            (("doi tra", "tra hang", "hoan tien"), "resolve_return_question", "get_return_support"),
            (
                ("thanh toan", "giao dich", "vnpay"),
                "resolve_payment_question",
                "get_payment_support",
            ),
            (("voucher", "ma giam gia", "khuyen mai"), "find_promotions", "get_promotions"),
            (
                ("flash sale", "flashsale", "deal soc", "gio vang"),
                "check_flash_sale",
                "get_flash_sales",
            ),
        )
        for phrases, goal, task in secondary_routes:
            if any(phrase in normalized for phrase in phrases):
                goals.append(goal)
                tasks.append(task)

        if any(term in normalized for term in ("chua biet gia", "gia ca", "khoang gia")):
            goals.append("understand_price_range")
        if any(
            term in normalized
            for term in (
                "nen mua",
                "loai nao",
                "dang bot",
                "dang hat",
                "hat hay bot",
                "nguyen hat hay bot",
            )
        ):
            goals.append("understand_product_options")
            tasks.append("explain_product_options")

        has_product_task = bool(set(tasks).intersection({"search_products", "recommend_products"}))
        contextual_modifier = _is_contextual_modifier(
            normalized,
            entities,
            constraints,
            preferences,
            facts,
        )
        if has_product_task and not (contextual_modifier and not entities.get("category")):
            product_type = _extract_product_type(
                text,
                vocabulary=vocabulary,
                category=str(entities.get("category", "")),
                brand=str(entities.get("brand", "")),
            )
            if product_type:
                entities["product_type"] = product_type
        if not has_product_task:
            query = ""
        elif product_type:
            query = product_type
        elif scenario:
            query = scenario.label
        else:
            query = (
                ""
                if contextual_modifier
                else _product_query(text)
            )
        if query:
            entities["query"] = query

        if recipient or occasion:
            inferences["possible_discovery_mode"] = "gift"
            if not product_type:
                facts["open_need"] = text[:200]
        elif scenario and not product_type:
            facts["open_need"] = scenario.label

        return QueryUnderstanding(
            primary_intent=str(primary),
            goals=tuple(dict.fromkeys(goals)),
            entities=entities,
            constraints=constraints,
            preferences=preferences,
            exclusions=exclusions,
            facts=facts,
            inferences=inferences,
            tasks=tuple(dict.fromkeys(tasks)),
            confidence=0.72,
        )

    @staticmethod
    def _inherit_conversation_intent(
        understanding: QueryUnderstanding,
        *,
        state: ConversationState,
    ) -> QueryUnderstanding:
        """Treat terse slot answers as continuation of the active shopping goal."""
        if (
            understanding.primary_intent == AssistantIntent.PRODUCT_SEARCH
            and "recommend_products" in state.active_goals
            and (
                understanding.entities
                or understanding.preferences
                or understanding.facts
                or set(understanding.constraints) - {"in_stock"}
            )
        ):
            tasks = tuple(
                dict.fromkeys(
                    task
                    for task in (*understanding.tasks, "recommend_products")
                    if task != "search_products"
                )
            )
            return replace(
                understanding,
                primary_intent=AssistantIntent.PRODUCT_RECOMMENDATION,
                goals=tuple(dict.fromkeys((*understanding.goals, "recommend_products"))),
                tasks=tasks,
            )
        return understanding

    @classmethod
    def _validated_model_output(
        cls,
        raw: dict[str, Any],
        *,
        vocabulary: dict[str, list[dict[str, str]]],
    ) -> QueryUnderstanding:
        intents = {str(item) for item in AssistantIntent}
        primary = str(raw.get("primary_intent", "")).strip().casefold()
        if primary not in intents:
            primary = AssistantIntent.PRODUCT_SEARCH
        tasks = tuple(
            item for item in _string_list(raw.get("tasks"), limit=12) if item in ALLOWED_TASKS
        )
        entities = _safe_dict(raw.get("entities"))
        entities = cls._validate_catalog_entities(entities, vocabulary=vocabulary)
        try:
            confidence = max(0.0, min(float(raw.get("confidence", 0.0)), 1.0))
        except (TypeError, ValueError, OverflowError):
            confidence = 0.0
        constraints = cls._normalize_constraints(_safe_dict(raw.get("constraints")))
        return QueryUnderstanding(
            primary_intent=primary,
            goals=tuple(_string_list(raw.get("goals"), limit=12)),
            entities=entities,
            constraints=constraints,
            preferences=_safe_dict(raw.get("preferences")),
            exclusions=_safe_dict(raw.get("exclusions")),
            facts=_safe_dict(raw.get("facts")),
            inferences=_safe_dict(raw.get("inferences")),
            tasks=tasks,
            confidence=confidence,
            security_refusal=primary == AssistantIntent.SECURITY_REFUSAL,
        )

    @staticmethod
    def _merge(
        deterministic: QueryUnderstanding,
        model: QueryUnderstanding,
    ) -> QueryUnderstanding:
        if model.security_refusal:
            return model
        model_entities = dict(model.entities)
        for hard_field in ("product_type", "category", "brand"):
            if hard_field not in deterministic.entities:
                model_entities.pop(hard_field, None)
        model_constraints = dict(model.constraints)
        for hard_field in ("price_min", "price_max", "budget"):
            if hard_field not in deterministic.constraints:
                model_constraints.pop(hard_field, None)
        constraints = {**model_constraints, **deterministic.constraints}
        if set(deterministic.constraints).intersection({"price_min", "price_max"}):
            constraints.pop("budget", None)
        elif deterministic.constraints.get("budget") == NO_PREFERENCE:
            constraints.pop("price_min", None)
            constraints.pop("price_max", None)
        return replace(
            model,
            goals=tuple(dict.fromkeys([*deterministic.goals, *model.goals])),
            entities={**model_entities, **deterministic.entities},
            constraints=constraints,
            preferences={**model.preferences, **deterministic.preferences},
            exclusions={**model.exclusions, **deterministic.exclusions},
            facts={**model.facts, **deterministic.facts},
            inferences={**deterministic.inferences, **model.inferences},
            tasks=tuple(dict.fromkeys([*deterministic.tasks, *model.tasks])),
            confidence=max(deterministic.confidence, model.confidence),
        )

    @staticmethod
    def _validate_catalog_entities(
        entities: dict[str, Any],
        *,
        vocabulary: dict[str, list[dict[str, str]]],
    ) -> dict[str, Any]:
        validated = dict(entities)
        # product_type is accepted only from deterministic catalog-grounded
        # extraction in the current user text, never from a model inference.
        validated.pop("product_type", None)
        for field, group in (("category", "categories"), ("brand", "brands")):
            value = str(validated.get(field, "")).strip()
            if not value:
                validated.pop(field, None)
                continue
            match = next(
                (
                    item["value"]
                    for item in vocabulary[group]
                    if _normalize(value) in {item["normalized"], _normalize(item["slug"])}
                ),
                "",
            )
            if match:
                validated[field] = match
            else:
                validated.pop(field, None)
        return sanitize_ai_payload(validated, max_depth=4)

    @staticmethod
    def _normalize_constraints(raw: dict[str, Any]) -> dict[str, Any]:
        aliases = {
            "min_price": "price_min",
            "budget_min": "price_min",
            "max_price": "price_max",
            "budget_max": "price_max",
            "budget_mode": "budget",
        }
        normalized: dict[str, Any] = {}
        for raw_key, value in raw.items():
            key = aliases.get(str(raw_key), str(raw_key))
            if key in {"price_min", "price_max"}:
                try:
                    number = float(value)
                except (TypeError, ValueError, OverflowError):
                    continue
                if number < 0 or number != number or number == float("inf"):
                    continue
                normalized[key] = round(number)
            elif str(value).strip().casefold() in {
                NO_PREFERENCE,
                "flexible",
                "unlimited",
                "không giới hạn",
                "khong gioi han",
                "tùy",
                "tuỳ",
            }:
                normalized[key] = NO_PREFERENCE
            elif key == "in_stock":
                normalized[key] = bool(value)
            else:
                normalized[key] = value
        return sanitize_ai_payload(normalized, max_depth=4)

    @staticmethod
    def _catalog_vocabulary() -> dict[str, list[dict[str, str]]]:
        categories = [
            {"value": name, "slug": slug, "normalized": _normalize(name)}
            for name, slug in Category.objects.filter(is_active=True, is_deleted=False)
            .order_by("name")
            .values_list("name", "slug")[:MAX_VOCABULARY_ITEMS]
        ]
        brands = [
            {"value": name, "slug": slug, "normalized": _normalize(name)}
            for name, slug in Brand.objects.filter(is_active=True, is_deleted=False)
            .order_by("name")
            .values_list("name", "slug")[:MAX_VOCABULARY_ITEMS]
        ]
        attributes = [
            {"value": name, "slug": code, "normalized": _normalize(name)}
            for name, code in Attribute.objects.order_by("name")
            .values_list("name", "code")
            .distinct()[:MAX_VOCABULARY_ITEMS]
        ]
        values = [
            {"value": value, "slug": "", "normalized": _normalize(value)}
            for value in AttributeValue.objects.order_by("value")
            .values_list("value", flat=True)
            .distinct()[:MAX_VOCABULARY_ITEMS]
        ]
        product_names = [
            {"value": name, "slug": "", "normalized": _normalize(name)}
            for name in ProductSelector.public_base()
            .order_by("name")
            .values_list("name", flat=True)[:1_000]
        ]
        return {
            "categories": categories,
            "brands": brands,
            "attributes": attributes,
            "attribute_values": values,
            "product_names": product_names,
        }

    @staticmethod
    def _prompt(
        *,
        text: str,
        state: ConversationState,
        vocabulary: dict[str, list[dict[str, str]]],
    ) -> str:
        payload = {
            "current_message": text,
            "conversation_state": state.to_dict(),
            "catalog_vocabulary": {
                key: [item["value"] for item in values]
                for key, values in vocabulary.items()
                if key != "product_names"
            },
            "allowed_intents": [str(item) for item in AssistantIntent],
            "allowed_tasks": sorted(ALLOWED_TASKS),
        }
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _parse_object(value: str) -> dict[str, Any] | None:
        cleaned = value.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
        try:
            parsed = json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            return None
        return parsed if isinstance(parsed, dict) else None


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", str(value).casefold())
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).replace("đ", "d")
    return " ".join(
        "".join(character if character.isalnum() else " " for character in ascii_value).split()
    )


def _contains_term(text: str, term: str) -> bool:
    return bool(term and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))


def _extract_first(text: str, mapping: dict[str, str]) -> str:
    return next((label for phrase, label in mapping.items() if _contains_term(text, phrase)), "")


def _safe_dict(value: Any) -> dict[str, Any]:
    return sanitize_ai_payload(value, max_depth=4) if isinstance(value, dict) else {}


def _string_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:120] for item in value[:limit] if str(item).strip()]


def _product_query(text: str) -> str:
    cleaned = re.sub(
        r"^(?:(?:tôi|mình|em)\s+)?"
        r"(?:muốn|cần|đang tìm|tìm|kiếm|đưa ra gợi ý|gợi ý|tư vấn)?\s*"
        r"(?:mua\s+)?",
        "",
        text.strip(),
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:dưới|không quá|tối đa|trên|từ|khoảng|tầm)\s+\d+(?:[.,]\d+)?\s*"
        r"(?:triệu|tr|nghìn|ngàn|k|vnd|đ|đồng)?\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return " ".join(cleaned.strip(" ,.;:!?-").split())[:200]


def _extract_product_type(
    text: str,
    *,
    vocabulary: dict[str, list[dict[str, str]]],
    category: str,
    brand: str,
) -> str:
    """Ground an explicit product noun phrase in catalog names/categories."""
    candidate = _product_query(text)
    candidate = re.split(
        r"\b(?:dành\s+cho|cho|dùng\s+để|dùng\s+cho|dùng\s+khi|để|phục\s+vụ|khi)\b",
        candidate,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    slot_marker = "|".join(
        sorted((re.escape(alias) for alias in slot_aliases()), key=len, reverse=True)
    )
    if slot_marker:
        candidate = re.split(
            rf"\b(?:{slot_marker})\b",
            candidate,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
    candidate = " ".join(candidate.strip(" ,.;:!?-").split())
    if not candidate:
        return ""

    original_tokens = candidate.split()
    normalized_tokens = _normalize(candidate).split()
    removable_prefixes = (
        ("mot", "chiec"),
        ("mot", "cai"),
        ("mot", "bo"),
        ("san", "pham"),
        ("do", "dung"),
    )
    for prefix in removable_prefixes:
        if tuple(normalized_tokens[: len(prefix)]) == prefix:
            original_tokens = original_tokens[len(prefix) :]
            normalized_tokens = normalized_tokens[len(prefix) :]
            break
    if not normalized_tokens:
        return ""

    normalized_brand = _normalize(brand).split()
    if normalized_brand and normalized_tokens[-len(normalized_brand) :] == normalized_brand:
        original_tokens = original_tokens[: -len(normalized_brand)]
        normalized_tokens = normalized_tokens[: -len(normalized_brand)]
    if not normalized_tokens:
        return ""

    generic_heads = {
        "qua",
        "do",
        "vat",
        "thu",
        "mon",
        "lua",
        "chon",
        "san",
        "pham",
        "nhu",
        "cau",
    }
    if normalized_tokens[0] in generic_heads:
        return ""

    if category:
        normalized_category = _normalize(category)
        for length in range(len(normalized_tokens), 0, -1):
            if " ".join(normalized_tokens[:length]) == normalized_category:
                return " ".join(original_tokens[:length])[:120]

    for length in range(len(normalized_tokens), 0, -1):
        normalized_candidate = " ".join(normalized_tokens[:length])
        if normalized_candidate in generic_heads:
            continue
        for item in vocabulary.get("product_names", []):
            canonical = _catalog_phrase(item["value"], normalized_candidate)
            if canonical:
                return canonical[:120]
    # A concrete noun phrase may legitimately describe a product type that the
    # marketplace does not carry yet. Keep that hard scope so retrieval returns
    # an honest empty result instead of substituting another category.
    return " ".join(original_tokens)[:120]


def _catalog_phrase(product_name: str, normalized_phrase: str) -> str:
    """Return catalog spelling for a normalized contiguous phrase."""
    normalized_tokens = _normalize(product_name).split()
    phrase_tokens = normalized_phrase.split()
    if not phrase_tokens:
        return ""
    width = len(phrase_tokens)
    original_tokens = product_name.split()
    for index in range(len(normalized_tokens) - width + 1):
        if normalized_tokens[index : index + width] == phrase_tokens:
            return " ".join(original_tokens[index : index + width])
    return ""


def _is_contextual_modifier(
    normalized_text: str,
    entities: dict[str, Any],
    constraints: dict[str, Any],
    preferences: dict[str, Any],
    facts: dict[str, Any],
) -> bool:
    """Keep a prior product query when a short follow-up only narrows constraints."""
    has_new_filter = bool(
        entities.get("category")
        or entities.get("brand")
        or preferences
        or facts
        or set(constraints).intersection({"price_min", "price_max", "budget"})
    )
    search_terms = ("tim", "mua", "can", "muon", "goi y", "tu van")
    return bool(
        has_new_filter
        and len(normalized_text.split()) <= 6
        and not any(term in normalized_text for term in search_terms)
    )

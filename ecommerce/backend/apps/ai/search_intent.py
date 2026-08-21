from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

MAX_SLOT_VALUES = 12

# These rules are deliberately small, reviewable, and deterministic. They fill
# the semantic gap for vague gift/occasion queries without letting an LLM turn
# an inference into an authoritative catalog filter.
OCCASION_RULES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "birthday": (("sinh nhật", "birthday"), ("quà tặng",)),
    "office": (("đi làm", "công sở", "văn phòng"), ("thời trang công sở", "phụ kiện")),
    "travel": (("du lịch", "đi biển"), ("phụ kiện du lịch", "thời trang")),
    "wedding": (("đám cưới", "lễ cưới"), ("quà tặng", "trang sức")),
}

RECIPIENT_RULES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "girlfriend": (
        ("bạn gái", "người yêu nữ", "girlfriend"),
        ("mỹ phẩm", "trang sức", "phụ kiện", "nước hoa", "túi xách"),
    ),
    "boyfriend": (
        ("bạn trai", "người yêu nam", "boyfriend"),
        ("đồng hồ", "phụ kiện", "thời trang nam", "nước hoa"),
    ),
    "mother": (("mẹ", "má", "mẹ tôi"), ("chăm sóc sức khỏe", "mỹ phẩm", "thời trang")),
    "father": (("bố", "ba", "cha"), ("đồng hồ", "thời trang nam", "chăm sóc sức khỏe")),
    "child": (("trẻ em", "bé", "con nhỏ"), ("đồ chơi", "thời trang trẻ em", "sách")),
}

COMBINED_CATEGORY_RULES: dict[tuple[str, str], tuple[str, ...]] = {
    ("birthday", "girlfriend"): ("mỹ phẩm", "trang sức", "phụ kiện", "nước hoa", "túi xách"),
    ("birthday", "boyfriend"): ("đồng hồ", "phụ kiện", "thời trang nam", "nước hoa"),
}

OCCASION_LABELS = {
    "birthday": "sinh nhật",
    "office": "đi làm",
    "travel": "du lịch",
    "wedding": "đám cưới",
}
RECIPIENT_LABELS = {
    "girlfriend": "bạn gái",
    "boyfriend": "bạn trai",
    "mother": "mẹ",
    "father": "bố",
    "child": "trẻ em",
}


def _clean_text(value: Any, *, limit: int = 100) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def _clean_list(value: Any, *, limit: int = MAX_SLOT_VALUES) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value[:limit]:
        normalized = _clean_text(item)
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def _matched_rule(query: str, rules: dict[str, tuple[tuple[str, ...], tuple[str, ...]]]) -> str:
    normalized = query.casefold()
    for canonical, (phrases, _categories) in rules.items():
        if any(phrase in normalized for phrase in phrases):
            return canonical
    return ""


@dataclass(frozen=True, slots=True)
class StructuredSearchIntent:
    intent_type: str
    keywords: tuple[str, ...]
    filters: dict[str, Any]
    category_hints: tuple[str, ...] = ()
    attributes: dict[str, tuple[str, ...]] = field(default_factory=dict)
    occasion: str = ""
    recipient: str = ""
    confidence: float = 0.0

    @property
    def expanded_query(self) -> str:
        terms = [*self.keywords, *self.category_hints]
        for values in self.attributes.values():
            terms.extend(values)
        return " ".join(dict.fromkeys(term for term in terms if term))

    def as_dict(self) -> dict[str, Any]:
        return {
            "intent_type": self.intent_type,
            "keywords": list(self.keywords),
            "filters": {
                key: str(value) if isinstance(value, Decimal) else value
                for key, value in self.filters.items()
            },
            "slots": {
                "category_hints": list(self.category_hints),
                "price_range": {
                    "min": self.filters.get("price_min"),
                    "max": self.filters.get("price_max"),
                },
                "attributes": {key: list(values) for key, values in self.attributes.items()},
                "occasion": self.occasion or None,
                "recipient": self.recipient or None,
            },
            "confidence": round(self.confidence, 3),
        }


class SearchIntentParser:
    @classmethod
    def parse(
        cls,
        *,
        query: str,
        raw_intent: Any,
        validated_filters: dict[str, Any],
    ) -> StructuredSearchIntent:
        raw = raw_intent if isinstance(raw_intent, dict) else {}
        slots = raw.get("slots") if isinstance(raw.get("slots"), dict) else {}
        keywords = _clean_list(raw.get("keywords")) or ([query] if query else [])

        occasion = _clean_text(slots.get("occasion"), limit=40).casefold()
        recipient = _clean_text(slots.get("recipient"), limit=40).casefold()
        deterministic_occasion = _matched_rule(query, OCCASION_RULES)
        deterministic_recipient = _matched_rule(query, RECIPIENT_RULES)
        occasion = deterministic_occasion or occasion
        recipient = deterministic_recipient or recipient

        category_hints = _clean_list(slots.get("category_hints"))
        if occasion in OCCASION_RULES:
            category_hints.extend(OCCASION_RULES[occasion][1])
        if recipient in RECIPIENT_RULES:
            category_hints.extend(RECIPIENT_RULES[recipient][1])
        category_hints.extend(COMBINED_CATEGORY_RULES.get((occasion, recipient), ()))
        category_hints = list(dict.fromkeys(category_hints))[:MAX_SLOT_VALUES]

        raw_attributes = slots.get("attributes")
        attributes: dict[str, tuple[str, ...]] = {}
        if isinstance(raw_attributes, dict):
            for raw_name, raw_values in list(raw_attributes.items())[:8]:
                name = _clean_text(raw_name, limit=60)
                values = tuple(_clean_list(raw_values, limit=8))
                if name and values:
                    attributes[name] = values

        intent_type = _clean_text(raw.get("intent_type"), limit=40) or (
            "gift_discovery" if occasion or recipient else "product_search"
        )
        try:
            confidence = float(raw.get("confidence", 0.0))
        except (TypeError, ValueError, OverflowError):
            confidence = 0.0
        confidence = min(max(confidence, 0.0), 1.0)
        if deterministic_occasion or deterministic_recipient:
            confidence = max(confidence, 0.75)

        return StructuredSearchIntent(
            intent_type=intent_type,
            keywords=tuple(keywords[:MAX_SLOT_VALUES]),
            filters={
                key: value
                for key, value in validated_filters.items()
                if key
                in {
                    "category",
                    "brand",
                    "price_min",
                    "price_max",
                    "rating_min",
                    "in_stock",
                    "shop",
                }
            },
            category_hints=tuple(category_hints),
            attributes=attributes,
            occasion=occasion,
            recipient=recipient,
            confidence=confidence,
        )

    @staticmethod
    def controlled_explanation(intent: StructuredSearchIntent) -> str:
        constraints: list[str] = []
        if intent.category_hints:
            constraints.append("nhóm " + ", ".join(intent.category_hints[:3]))
        if intent.occasion:
            constraints.append(f"dịp {OCCASION_LABELS.get(intent.occasion, intent.occasion)}")
        if intent.recipient:
            constraints.append(
                f"người nhận {RECIPIENT_LABELS.get(intent.recipient, intent.recipient)}"
            )
        price_min = intent.filters.get("price_min")
        price_max = intent.filters.get("price_max")
        if price_min is not None or price_max is not None:
            if price_min is not None and price_max is not None:
                constraints.append(f"giá {int(price_min):,}–{int(price_max):,} ₫")
            elif price_max is not None:
                constraints.append(f"giá không quá {int(price_max):,} ₫")
            else:
                constraints.append(f"giá từ {int(price_min):,} ₫")
        if intent.attributes:
            values = [value for items in intent.attributes.values() for value in items]
            if values:
                constraints.append("thuộc tính " + ", ".join(values[:3]))
        if not constraints:
            return "Kết quả được xếp hạng theo từ khóa và dữ liệu sản phẩm hiện có."
        return "Gợi ý dựa trên " + "; ".join(constraints) + "."

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings

from .state import ConversationState


class GroundedRecommendationEngine:
    """Rank catalog candidates and explain only verifiable fields."""

    def rank(
        self,
        *,
        products: list[dict[str, Any]],
        state: ConversationState,
        context_terms: Iterable[str] = (),
    ) -> list[dict[str, Any]]:
        terms = tuple(
            dict.fromkeys(str(item).strip() for item in context_terms if str(item).strip())
        )
        ranked = [
            self._score(product=product, state=state, context_terms=terms) for product in products
        ]
        ranked.sort(
            key=lambda item: (
                bool(item["compatibility_warnings"]),
                -item["recommendation_score"],
                str(item["product"].get("id", "")),
            )
        )
        return ranked

    def _score(
        self,
        *,
        product: dict[str, Any],
        state: ConversationState,
        context_terms: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        score = 0.0
        reasons: list[str] = []
        warnings = self._compatibility_warnings(product=product, state=state)

        category = _value(state, "category")
        if category and _normalize(category) == _normalize(product.get("category_name", "")):
            score += settings.AI_ASSISTANT_RANK_CATEGORY_WEIGHT
            reasons.append(f"thuộc nhóm {product['category_name']} bạn đang tìm")

        product_type = _value(state, "product_type")
        normalized_product_name = f" {_normalize(product.get('name', ''))} "
        if product_type and f" {_normalize(product_type)} " in normalized_product_name:
            score += settings.AI_ASSISTANT_RANK_CATEGORY_WEIGHT
            reasons.append(f"đúng loại sản phẩm {product_type}")

        brand = _value(state, "brand")
        if brand and _normalize(brand) == _normalize(product.get("brand_name", "")):
            score += settings.AI_ASSISTANT_RANK_BRAND_WEIGHT
            reasons.append(f"đúng thương hiệu {product['brand_name']}")

        price_max = _decimal(_value(state, "price_max"))
        product_min = _decimal(product.get("min_price"))
        if price_max is not None and product_min is not None and product_min <= price_max:
            score += settings.AI_ASSISTANT_RANK_PRICE_WEIGHT
            reasons.append("nằm trong ngân sách tối đa")

        document = _product_document(product)
        matched_context = [
            term for term in context_terms if _normalize(term) and _normalize(term) in document
        ]
        if matched_context:
            score += settings.AI_ASSISTANT_RANK_PREFERENCE_WEIGHT
            reasons.append("có thông tin về " + ", ".join(matched_context[:2]))
        matched_preferences: list[str] = []
        for entry in state.preferences.values():
            value = entry.get("value") if isinstance(entry, dict) else None
            for term in _flatten_terms(value):
                if _normalize(term) and _normalize(term) in document:
                    matched_preferences.append(str(term))
        if matched_preferences:
            score += settings.AI_ASSISTANT_RANK_PREFERENCE_WEIGHT
            reasons.append("có dữ liệu phù hợp với " + ", ".join(matched_preferences[:2]))

        rating = _decimal(product.get("rating_average")) or Decimal("0")
        rating_count = max(0, int(product.get("rating_count") or 0))
        if rating_count:
            score += min(float(rating) / 5, 1.0) * settings.AI_ASSISTANT_RANK_RATING_WEIGHT

        if product.get("stock_status") == "in_stock":
            score += settings.AI_ASSISTANT_RANK_STOCK_WEIGHT
            reasons.append("đang còn hàng")
        if warnings:
            score -= settings.AI_ASSISTANT_RANK_INCOMPATIBILITY_PENALTY

        if not reasons:
            reasons.append("khớp gần nhất với dữ liệu sản phẩm hiện có")
        return {
            "product": product,
            "recommendation_score": round(max(0.0, score), 4),
            "reasons": reasons[:3],
            "compatibility_warnings": warnings,
            "kind": ("alternative" if warnings else "personalized" if matched_context else "exact"),
        }

    @staticmethod
    def _compatibility_warnings(
        *,
        product: dict[str, Any],
        state: ConversationState,
    ) -> list[str]:
        unavailable = _flatten_terms(_value(state, "unavailable_equipment"))
        if not unavailable:
            return []
        warnings: list[str] = []
        attributes = product.get("attributes")
        if not isinstance(attributes, dict):
            return warnings
        for code, raw in attributes.items():
            normalized_code = _normalize(code)
            raw_text = " ".join(_flatten_terms(raw))
            normalized_value = _normalize(raw_text)
            if not (
                normalized_code.startswith("requires ")
                or "yeu cau" in normalized_code
                or "can thiet bi" in normalized_code
            ):
                continue
            if normalized_value in {"khong", "false", "no", "0", "none"}:
                continue
            for equipment in unavailable:
                normalized_equipment = _normalize(equipment)
                requirement_matches = (
                    normalized_equipment in normalized_code
                    or normalized_equipment in normalized_value
                )
                if requirement_matches:
                    warnings.append(
                        f"sản phẩm yêu cầu {equipment}, nhưng bạn nói chưa có thiết bị này"
                    )
        return list(dict.fromkeys(warnings))[:3]


def _value(state: ConversationState, field: str) -> Any:
    return state.effective_values(field)


def _normalize(value: Any) -> str:
    decomposed = unicodedata.normalize("NFD", str(value).casefold())
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).replace("đ", "d")
    return " ".join(
        "".join(character if character.isalnum() else " " for character in ascii_value).split()
    )


def _flatten_terms(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [str(item) for item in value.values() if item not in (None, "")]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)] if value not in (None, "") else []


def _product_document(product: dict[str, Any]) -> str:
    parts = [
        product.get("name", ""),
        product.get("category_name", ""),
        product.get("brand_name", ""),
        product.get("short_description", ""),
    ]
    attributes = product.get("attributes")
    if isinstance(attributes, dict):
        for key, value in attributes.items():
            parts.extend((key, *_flatten_terms(value)))
    return _normalize(" ".join(str(part) for part in parts if part))


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None

from __future__ import annotations

import re
from typing import Any

from django.conf import settings

from .discovery import search_terms_for_usage
from .schemas import (
    AssistantIntent,
    AssistantPlan,
    MissingInformation,
    PlanAction,
    QueryUnderstanding,
)
from .slots import NO_PREFERENCE, is_no_preference
from .state import ConversationState

ORDER_CODE_RE = re.compile(r"\b(?:S?ORD)-[A-Z0-9-]{6,50}\b", re.IGNORECASE)


class AssistantPlanner:
    def plan(
        self,
        *,
        text: str,
        understanding: QueryUnderstanding,
        state: ConversationState,
    ) -> AssistantPlan:
        if understanding.security_refusal:
            return AssistantPlan(
                action=PlanAction.REFUSE,
                rationale="The request attempts to access instructions or protected data.",
            )

        missing = self._missing_information(understanding=understanding, state=state)
        tool_calls = self._tool_calls(
            text=text,
            understanding=understanding,
            state=state,
        )
        high_value_missing = tuple(
            item
            for item in missing
            if item.importance >= settings.AI_ASSISTANT_CLARIFICATION_THRESHOLD
        )[:2]
        product_tools = any(call["name"] == "search_products" for call in tool_calls)

        if high_value_missing and product_tools:
            action = PlanAction.ASK_AND_SEARCH
        elif high_value_missing:
            action = PlanAction.ASK
        elif len(tool_calls) > 1:
            action = PlanAction.MULTI_TOOL
        elif tool_calls:
            action = PlanAction.SEARCH
        else:
            action = PlanAction.ANSWER

        return AssistantPlan(
            action=action,
            tasks=understanding.tasks,
            missing_information=high_value_missing,
            tool_calls=tuple(tool_calls),
            rationale=(
                "Ask only the highest-value unknowns while executing safe available tasks."
                if high_value_missing
                else "The collected state is sufficient for the selected grounded tools."
            ),
        )

    @staticmethod
    def _missing_information(
        *,
        understanding: QueryUnderstanding,
        state: ConversationState,
    ) -> tuple[MissingInformation, ...]:
        intent = understanding.primary_intent
        product_focus = next(
            (
                value
                for value in (
                    _state_value(state, "product_type"),
                    _state_value(state, "category"),
                    _state_value(state, "query"),
                    _state_value(state, "open_need"),
                )
                if value and not is_no_preference(value)
            ),
            None,
        )
        budget_known = bool(
            _state_value(state, "price_min") is not None
            or _state_value(state, "price_max") is not None
            or _state_value(state, "budget") == NO_PREFERENCE
        )
        missing: list[MissingInformation] = []

        if intent in {
            AssistantIntent.PRODUCT_SEARCH,
            AssistantIntent.PRODUCT_RECOMMENDATION,
            AssistantIntent.PRODUCT_COMPARE,
        }:
            if not product_focus:
                missing.append(
                    MissingInformation(
                        field="product_focus",
                        importance=1.0,
                        reason="Không có nhóm sản phẩm hoặc nhu cầu có thể dùng để tìm kiếm.",
                        question="Bạn muốn ưu tiên nhóm sản phẩm hoặc nhu cầu sử dụng nào?",
                    )
                )

        if intent == AssistantIntent.PRODUCT_RECOMMENDATION:
            is_gift = bool(_state_value(state, "recipient") or _state_value(state, "occasion"))
            has_interest = bool(
                _state_value(state, "interest")
                or _state_value(state, "usage")
                or _state_value(state, "category")
            )
            if is_gift and not has_interest:
                missing.append(
                    MissingInformation(
                        field="interest",
                        importance=0.96,
                        reason="Sở thích giúp loại bỏ những nhóm quà không phù hợp.",
                        question=(
                            "Người nhận thường thích đồ công nghệ, thời trang, làm đẹp, "
                            "trang sức hay nhóm nào khác?"
                        ),
                    )
                )
            if not budget_known:
                budget_importance = 0.92 if is_gift else 0.68
                missing.append(
                    MissingInformation(
                        field="budget",
                        importance=budget_importance,
                        reason="Ngân sách ảnh hưởng mạnh đến tập ứng viên.",
                        question=(
                            "Bạn dự định chi khoảng bao nhiêu? Bạn có thể nói một khoảng "
                            "hoặc “không giới hạn”."
                        ),
                    )
                )

        goals = set(understanding.goals)
        if "understand_product_options" in goals:
            has_equipment_fact = bool(
                _state_value(state, "available_equipment")
                or _state_value(state, "unavailable_equipment")
            )
            if not has_equipment_fact:
                missing.append(
                    MissingInformation(
                        field="available_equipment",
                        importance=0.95,
                        reason="Thiết bị sẵn có quyết định khả năng tương thích sản phẩm.",
                        question="Bạn đang có dụng cụ hoặc thiết bị nào để sử dụng sản phẩm?",
                    )
                )
            if not budget_known:
                missing.append(
                    MissingInformation(
                        field="budget",
                        importance=0.76,
                        reason="Khoảng giá giúp xếp hạng nhưng không ngăn việc giải thích trước.",
                        question="Bạn muốn tham khảo trong khoảng ngân sách nào?",
                    )
                )

        return tuple(sorted(missing, key=lambda item: item.importance, reverse=True))

    @staticmethod
    def _tool_calls(
        *,
        text: str,
        understanding: QueryUnderstanding,
        state: ConversationState,
    ) -> list[dict[str, Any]]:
        tasks = set(understanding.tasks)
        calls: list[dict[str, Any]] = []
        if tasks.intersection({"search_products", "recommend_products"}):
            query = str(_state_value(state, "query") or "").strip()
            category = _filter_value(state, "category")
            product_type = _filter_value(state, "product_type")
            is_underspecified_gift = bool(
                understanding.primary_intent == AssistantIntent.PRODUCT_RECOMMENDATION
                and (_state_value(state, "recipient") or _state_value(state, "occasion"))
                and not (
                    _state_value(state, "interest")
                    or _state_value(state, "usage")
                    or category
                    or product_type
                )
            )
            if (query or category or product_type) and not is_underspecified_gift:
                arguments: dict[str, Any] = {
                    "query": str(product_type or category or query),
                    "limit": settings.AI_ASSISTANT_RESULT_LIMIT,
                    "in_stock": True,
                }
                if product_type:
                    arguments["product_type"] = product_type
                for field in ("category", "brand", "price_min", "price_max"):
                    value = _filter_value(state, field)
                    if value is not None:
                        arguments[field] = value
                query_terms = search_terms_for_usage(_state_value(state, "usage"))
                if query_terms:
                    arguments["query_terms"] = list(query_terms)
                calls.append({"name": "search_products", "arguments": arguments})
        if "compare_products" in tasks and len(state.last_product_ids) >= 2:
            calls.append(
                {
                    "name": "compare_products",
                    "arguments": {"product_ids": state.last_product_ids[:4]},
                }
            )
        if "get_policy" in tasks:
            calls.append({"name": "get_policy", "arguments": {"topic": text}})
        if "get_order_status" in tasks:
            match = ORDER_CODE_RE.search(text)
            calls.append(
                {
                    "name": "get_order_status",
                    "arguments": {"order_code": match.group(0).upper() if match else ""},
                }
            )
        if "get_return_support" in tasks:
            match = ORDER_CODE_RE.search(text)
            calls.append(
                {
                    "name": "get_return_support",
                    "arguments": {"order_code": match.group(0).upper() if match else ""},
                }
            )
        if "get_payment_support" in tasks:
            match = ORDER_CODE_RE.search(text)
            calls.append(
                {
                    "name": "get_payment_support",
                    "arguments": {"order_code": match.group(0).upper() if match else ""},
                }
            )
        if "get_promotions" in tasks:
            calls.append(
                {
                    "name": "get_promotions",
                    "arguments": {"limit": settings.AI_ASSISTANT_RESULT_LIMIT},
                }
            )
        if "get_flash_sales" in tasks:
            calls.append(
                {
                    "name": "get_flash_sales",
                    "arguments": {"limit": settings.AI_ASSISTANT_RESULT_LIMIT},
                }
            )
        if "human_handoff" in tasks:
            calls.append({"name": "human_handoff", "arguments": {"reason": text}})
        return calls


def _state_value(state: ConversationState, field: str) -> Any:
    return state.effective_values(field)


def _filter_value(state: ConversationState, field: str) -> Any:
    value = _state_value(state, field)
    return None if is_no_preference(value) else value

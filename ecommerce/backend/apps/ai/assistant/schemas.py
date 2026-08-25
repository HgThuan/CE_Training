from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class AssistantIntent(StrEnum):
    PRODUCT_SEARCH = "product_search"
    PRODUCT_RECOMMENDATION = "product_recommendation"
    PRODUCT_COMPARE = "product_compare"
    ORDER_STATUS = "order_status"
    RETURN_SUPPORT = "return_support"
    PAYMENT_SUPPORT = "payment_support"
    PROMOTION = "promotion"
    POLICY = "policy"
    HUMAN_HANDOFF = "human_handoff"
    OUT_OF_SCOPE = "out_of_scope"
    SECURITY_REFUSAL = "security_refusal"


class PlanAction(StrEnum):
    ASK = "ask"
    SEARCH = "search"
    ANSWER = "answer"
    ASK_AND_SEARCH = "ask_and_search"
    MULTI_TOOL = "multi_tool"
    REFUSE = "refuse"


ALLOWED_TASKS = {
    "search_products",
    "recommend_products",
    "compare_products",
    "explain_product_options",
    "get_order_status",
    "get_return_support",
    "get_payment_support",
    "get_promotions",
    "get_flash_sales",
    "get_policy",
    "human_handoff",
}


@dataclass(frozen=True, slots=True)
class MissingInformation:
    field: str
    importance: float
    reason: str = ""
    question: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class QueryUnderstanding:
    primary_intent: str = AssistantIntent.PRODUCT_SEARCH
    goals: tuple[str, ...] = ()
    entities: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    exclusions: dict[str, Any] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)
    inferences: dict[str, Any] = field(default_factory=dict)
    tasks: tuple[str, ...] = ()
    confidence: float = 0.0
    security_refusal: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AssistantPlan:
    action: str
    tasks: tuple[str, ...] = ()
    missing_information: tuple[MissingInformation, ...] = ()
    tool_calls: tuple[dict[str, Any], ...] = ()
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class ToolResult:
    name: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error_code: str = ""
    message: str = ""
    duration_ms: int = 0

    def public_data(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "data": self.data,
            "error_code": self.error_code,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class AssistantResponse:
    message: str
    intent: str
    attachments: tuple[dict[str, Any], ...] = ()
    clarification: dict[str, Any] = field(default_factory=dict)
    suggested_replies: tuple[str, ...] = ()
    grounded_product_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AssistantEvent:
    type: str
    text: str = ""
    stage: str = ""
    conversation_id: str = ""
    message: dict[str, Any] | None = None
    code: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value not in ("", None)}

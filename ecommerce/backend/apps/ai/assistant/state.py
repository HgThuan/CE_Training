from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.ai.models import ChatSession, sanitize_ai_payload

from .schemas import QueryUnderstanding
from .slots import NO_PREFERENCE

STATE_VERSION = 1
MAX_STATE_ITEMS = 30


@dataclass(slots=True)
class ConversationState:
    version: int = STATE_VERSION
    active_goals: list[str] = field(default_factory=list)
    facts: dict[str, dict[str, Any]] = field(default_factory=dict)
    inferences: dict[str, dict[str, Any]] = field(default_factory=dict)
    constraints: dict[str, dict[str, Any]] = field(default_factory=dict)
    preferences: dict[str, dict[str, Any]] = field(default_factory=dict)
    exclusions: dict[str, dict[str, Any]] = field(default_factory=dict)
    task_status: dict[str, str] = field(default_factory=dict)
    last_product_ids: list[str] = field(default_factory=list)
    pending_slots: list[str] = field(default_factory=list)

    @classmethod
    def from_context(cls, context: Any) -> ConversationState:
        if not isinstance(context, dict):
            return cls()
        raw = context.get("assistant_state")
        if not isinstance(raw, dict) or raw.get("version") != STATE_VERSION:
            return cls()
        try:
            return cls(
                active_goals=_clean_string_list(raw.get("active_goals")),
                facts=_clean_mapping(raw.get("facts")),
                inferences=_clean_mapping(raw.get("inferences")),
                constraints=_clean_mapping(raw.get("constraints")),
                preferences=_clean_mapping(raw.get("preferences")),
                exclusions=_clean_mapping(raw.get("exclusions")),
                task_status={
                    str(key)[:80]: str(value)[:30]
                    for key, value in _as_dict(raw.get("task_status")).items()
                },
                last_product_ids=_clean_string_list(raw.get("last_product_ids"), limit=20),
                pending_slots=_clean_string_list(raw.get("pending_slots"), limit=12),
            )
        except (TypeError, ValueError):
            return cls()

    def effective_values(self, field_name: str) -> Any:
        for source in (self.constraints, self.facts, self.preferences):
            entry = source.get(field_name)
            if isinstance(entry, dict) and "value" in entry:
                return entry["value"]
        return None

    def to_dict(self) -> dict[str, Any]:
        return sanitize_ai_payload(asdict(self), max_depth=6)


class ConversationStateRepository:
    @classmethod
    def load(cls, session: ChatSession) -> ConversationState:
        return ConversationState.from_context(session.context)

    @classmethod
    def merge_understanding(
        cls,
        *,
        session: ChatSession,
        understanding: QueryUnderstanding,
    ) -> tuple[ChatSession, ConversationState]:
        with transaction.atomic():
            locked = ChatSession.objects.select_for_update().get(pk=session.pk)
            state = ConversationState.from_context(locked.context)
            turn = locked.turn_count
            state.active_goals = _merge_unique(state.active_goals, understanding.goals)
            cls._merge_values(state.facts, understanding.facts, source="user", turn=turn)
            cls._merge_values(
                state.inferences,
                understanding.inferences,
                source="assistant_inference",
                turn=turn,
                confidence=understanding.confidence,
            )
            cls._merge_values(
                state.constraints,
                {**understanding.entities, **understanding.constraints},
                source="user",
                turn=turn,
            )
            if understanding.constraints.get("budget") == NO_PREFERENCE:
                state.constraints.pop("price_min", None)
                state.constraints.pop("price_max", None)
            elif any(key in understanding.constraints for key in ("price_min", "price_max")):
                state.constraints.pop("budget", None)
            cls._merge_values(
                state.preferences,
                understanding.preferences,
                source="user",
                turn=turn,
            )
            cls._merge_values(
                state.exclusions,
                understanding.exclusions,
                source="user",
                turn=turn,
            )
            for task in understanding.tasks:
                state.task_status[task] = "pending"

            context = dict(locked.context or {})
            context["assistant_state"] = state.to_dict()
            locked.context = context
            locked.last_active_at = timezone.now()
            locked.save(update_fields=("context", "last_active_at", "updated_at"))
            session.context = context
            return locked, state

    @classmethod
    def record_pending_slots(
        cls,
        *,
        session: ChatSession,
        fields: list[str],
    ) -> ConversationState:
        with transaction.atomic():
            locked = ChatSession.objects.select_for_update().get(pk=session.pk)
            state = ConversationState.from_context(locked.context)
            state.pending_slots = list(dict.fromkeys(str(item)[:80] for item in fields))[:12]
            context = dict(locked.context or {})
            context["assistant_state"] = state.to_dict()
            locked.context = context
            locked.save(update_fields=("context", "updated_at"))
            session.context = context
            return state

    @classmethod
    def record_results(
        cls,
        *,
        session: ChatSession,
        completed_tasks: list[str],
        product_ids: list[str],
    ) -> ConversationState:
        with transaction.atomic():
            locked = ChatSession.objects.select_for_update().get(pk=session.pk)
            state = ConversationState.from_context(locked.context)
            for task in completed_tasks:
                state.task_status[task] = "completed"
            state.last_product_ids = list(dict.fromkeys(product_ids))[:20]
            context = dict(locked.context or {})
            context["assistant_state"] = state.to_dict()
            locked.context = context
            locked.save(update_fields=("context", "updated_at"))
            session.context = context
            return state

    @staticmethod
    def _merge_values(
        target: dict[str, dict[str, Any]],
        incoming: dict[str, Any],
        *,
        source: str,
        turn: int,
        confidence: float = 1.0,
    ) -> None:
        if not isinstance(incoming, dict):
            return
        for key, value in list(incoming.items())[:MAX_STATE_ITEMS]:
            normalized_key = str(key).strip()[:80]
            if not normalized_key or value in (None, "", [], {}):
                continue
            target[normalized_key] = {
                "value": sanitize_ai_payload(value, max_depth=4),
                "source": source,
                "turn": max(0, int(turn)),
                "confidence": max(0.0, min(float(confidence), 1.0)),
            }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_mapping(value: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for key, item in list(_as_dict(value).items())[:MAX_STATE_ITEMS]:
        if isinstance(item, dict) and "value" in item:
            result[str(key)[:80]] = item
    return result


def _clean_string_list(value: Any, *, limit: int = MAX_STATE_ITEMS) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:120] for item in value[:limit] if str(item).strip()]


def _merge_unique(current: list[str], incoming: tuple[str, ...]) -> list[str]:
    return list(dict.fromkeys([*current, *(str(item)[:120] for item in incoming)]))[
        -MAX_STATE_ITEMS:
    ]

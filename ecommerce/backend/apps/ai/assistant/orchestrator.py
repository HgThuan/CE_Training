from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ai.models import AIRequestLog, ChatMessage, ChatSession, sanitize_ai_text
from apps.common.models import SiteSetting

from .planner import AssistantPlanner
from .responses import GroundedResponseComposer, ResponseValidator
from .schemas import AssistantEvent, ToolResult
from .state import ConversationStateRepository
from .tooling import AssistantToolRegistry, ToolContext
from .understanding import QueryUnderstandingService

logger = logging.getLogger(__name__)


class ShoppingAssistant:
    MAX_TURNS_PER_CONVERSATION = 60
    MAX_MESSAGE_LENGTH = 1_000

    def __init__(
        self,
        *,
        understanding: QueryUnderstandingService | None = None,
        planner: AssistantPlanner | None = None,
        tools: AssistantToolRegistry | None = None,
        composer: GroundedResponseComposer | None = None,
        monotonic_fn=None,
    ) -> None:
        self._understanding = understanding or QueryUnderstandingService()
        self._planner = planner or AssistantPlanner()
        self._tools = tools or AssistantToolRegistry()
        self._composer = composer or GroundedResponseComposer()
        self._monotonic = monotonic_fn or time.monotonic

    def handle_turn(
        self,
        *,
        session: ChatSession,
        user_text: str,
        user: Any,
    ) -> Iterator[AssistantEvent]:
        message_text = sanitize_ai_text(
            user_text,
            max_length=self.MAX_MESSAGE_LENGTH,
        ).strip()
        if not message_text:
            yield AssistantEvent(
                type="error",
                text="Vui lòng nhập nội dung cần tư vấn.",
                code="empty_message",
            )
            return
        if not self.is_enabled():
            yield AssistantEvent(
                type="error",
                text="Trợ lý mua sắm đang tạm dừng. Bạn vẫn có thể dùng tìm kiếm thông thường.",
                code="assistant_disabled",
            )
            return

        started = self._monotonic()
        session, rejection = self._reserve_turn(
            session=session,
            user_text=message_text,
            user=user,
        )
        if rejection is not None:
            yield rejection
            return

        yield AssistantEvent(type="stage", stage="understanding")
        state = ConversationStateRepository.load(session)
        try:
            understanding = self._understanding.understand(
                text=message_text,
                state=state,
                user=user,
            )
            session, state = ConversationStateRepository.merge_understanding(
                session=session,
                understanding=understanding,
            )
            yield AssistantEvent(type="stage", stage="planning")
            plan = self._planner.plan(
                text=message_text,
                understanding=understanding,
                state=state,
            )
            state = ConversationStateRepository.record_pending_slots(
                session=session,
                fields=[item.field for item in plan.missing_information],
            )
            results: list[ToolResult] = []
            if plan.tool_calls:
                yield AssistantEvent(type="stage", stage="retrieving")
            for call in plan.tool_calls:
                result = self._tools.execute(
                    name=str(call.get("name", "")),
                    arguments=(
                        call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
                    ),
                    context=ToolContext(user=user, session=session, state=state),
                )
                results.append(result)
                self._store_tool_result(session=session, result=result)
            yield AssistantEvent(type="stage", stage="composing")
            response = self._composer.compose(
                understanding=understanding,
                plan=plan,
                state=state,
                results=results,
            )
            response = ResponseValidator.validate(response, results=results)
        except Exception as exc:
            logger.exception(
                "Shopping assistant orchestration failed",
                extra={"chat_session_id": str(session.pk)},
            )
            response_text = (
                "Mình chưa thể hoàn tất việc phân tích yêu cầu lúc này. "
                "Dữ liệu sản phẩm và tài khoản của bạn không bị thay đổi; bạn có thể thử lại."
            )
            log = self._write_log(
                session=session,
                user_text=message_text,
                response=response_text,
                latency_ms=_elapsed_ms(started, self._monotonic),
                status=AIRequestLog.Status.FALLBACK,
                error=exc,
                metadata={"stage": "orchestration"},
            )
            assistant_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content=response_text,
                attachments=[],
                ai_request_log=log,
            )
            yield from self._stream_text(response_text)
            yield AssistantEvent(
                type="done",
                message=self.serialize_message(assistant_message),
            )
            return

        successful_tools = {result.name for result in results if result.ok}
        completed_tasks = [
            task
            for task in plan.tasks
            if _task_completed(task=task, successful_tools=successful_tools)
        ]
        ConversationStateRepository.record_results(
            session=session,
            completed_tasks=completed_tasks,
            product_ids=list(response.grounded_product_ids),
        )
        log = self._write_log(
            session=session,
            user_text=message_text,
            response=response.message,
            latency_ms=_elapsed_ms(started, self._monotonic),
            status=AIRequestLog.Status.SUCCESS,
            metadata={
                "intent": response.intent,
                "goals": list(understanding.goals),
                "tasks": list(plan.tasks),
                "plan_action": plan.action,
                "tools_called": [result.name for result in results],
                "tool_status": {result.name: result.ok for result in results},
                "tool_latency_ms": {result.name: result.duration_ms for result in results},
                "clarification_fields": [item.field for item in plan.missing_information],
                "grounded_product_ids": list(response.grounded_product_ids),
            },
        )
        attachments = [*response.attachments]
        if response.suggested_replies:
            attachments.append(
                {
                    "type": "suggested_replies",
                    "suggestions": list(response.suggested_replies),
                }
            )
        assistant_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=response.message,
            tool_calls=[
                {
                    "name": result.name,
                    "ok": result.ok,
                    "error_code": result.error_code,
                }
                for result in results
            ]
            or None,
            attachments=attachments,
            ai_request_log=log,
        )
        yield from self._stream_text(response.message)
        yield AssistantEvent(type="done", message=self.serialize_message(assistant_message))

    @classmethod
    def _reserve_turn(
        cls,
        *,
        session: ChatSession,
        user_text: str,
        user: Any,
    ) -> tuple[ChatSession, AssistantEvent | None]:
        with transaction.atomic():
            locked = ChatSession.objects.select_for_update().get(pk=session.pk, user=user)
            if locked.status != ChatSession.Status.ACTIVE:
                return locked, AssistantEvent(
                    type="error",
                    text="Cuộc trò chuyện này đã đóng. Vui lòng bắt đầu cuộc trò chuyện mới.",
                    code="conversation_closed",
                )
            if locked.turn_count >= cls.MAX_TURNS_PER_CONVERSATION:
                locked.status = ChatSession.Status.CLOSED
                locked.save(update_fields=("status", "updated_at"))
                return locked, AssistantEvent(
                    type="error",
                    text="Cuộc trò chuyện đã đạt giới hạn. Vui lòng bắt đầu cuộc trò chuyện mới.",
                    code="turn_limit_reached",
                )
            ChatMessage.objects.create(
                session=locked,
                role=ChatMessage.Role.USER,
                content=user_text,
            )
            locked.turn_count += 1
            locked.last_active_at = timezone.now()
            fields = ["turn_count", "last_active_at", "updated_at"]
            if not locked.title:
                locked.title = user_text.splitlines()[0][:200]
                fields.append("title")
            locked.save(update_fields=fields)
            return locked, None

    @staticmethod
    def _store_tool_result(*, session: ChatSession, result: ToolResult) -> None:
        payload = json.dumps(result.public_data(), ensure_ascii=False, default=str)
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.TOOL,
            tool_call_id=f"assistant-{result.name}-{session.turn_count}",
            content=sanitize_ai_text(payload, max_length=4_000),
        )

    @staticmethod
    def _stream_text(text: str) -> Iterator[AssistantEvent]:
        paragraphs = text.split("\n\n")
        for index, paragraph in enumerate(paragraphs):
            suffix = "\n\n" if index < len(paragraphs) - 1 else ""
            yield AssistantEvent(type="delta", text=f"{paragraph}{suffix}")

    @staticmethod
    def _write_log(
        *,
        session: ChatSession,
        user_text: str,
        response: str,
        latency_ms: int,
        status: str,
        metadata: dict[str, Any],
        error: Exception | None = None,
    ) -> AIRequestLog | None:
        try:
            return AIRequestLog.objects.create(
                user=session.user,
                feature=AIRequestLog.Feature.CHAT_TURN,
                provider="assistant_orchestrator",
                model_name=str(settings.AI_MODEL),
                prompt_template_version="shopping-assistant-v1",
                prompt=user_text,
                response=response,
                latency_ms=latency_ms,
                status=status,
                error_code=getattr(error, "code", "assistant_error") if error else "",
                error_message=str(error) if error else "",
                metadata={"conversation_id": str(session.pk), **metadata},
            )
        except Exception:
            logger.warning("Could not persist assistant request log", exc_info=True)
            return None

    @staticmethod
    def serialize_message(message: ChatMessage) -> dict[str, Any]:
        feedback = getattr(message, "feedback", None)
        return {
            "id": str(message.pk),
            "conversation_id": str(message.session_id),
            "role": message.role,
            "content": message.content,
            "attachments": message.attachments,
            "feedback": (
                {
                    "rating": feedback.rating,
                    "resolved": feedback.resolved,
                    "comment": feedback.comment,
                }
                if feedback is not None
                else None
            ),
            "created_at": message.created_at.isoformat(),
        }

    @staticmethod
    def is_enabled() -> bool:
        return bool(
            settings.AI_FEATURES_ENABLED
            and SiteSetting.get_bool(
                "feature.ai_assistant.enabled",
                default=settings.AI_FEATURES_ENABLED,
            )
        )


def _elapsed_ms(started: float, monotonic) -> int:
    return max(0, round((monotonic() - started) * 1_000))


def _task_completed(*, task: str, successful_tools: set[str]) -> bool:
    tool_by_task = {
        "recommend_products": "search_products",
        "explain_product_options": "search_products",
    }
    return tool_by_task.get(task, task) in successful_tools

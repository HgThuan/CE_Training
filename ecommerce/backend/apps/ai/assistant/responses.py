from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from django.utils import timezone

from apps.ai.models import sanitize_ai_text

from .schemas import AssistantPlan, AssistantResponse, PlanAction, QueryUnderstanding, ToolResult
from .state import ConversationState


class GroundedResponseComposer:
    def compose(
        self,
        *,
        understanding: QueryUnderstanding,
        plan: AssistantPlan,
        state: ConversationState,
        results: list[ToolResult],
    ) -> AssistantResponse:
        if plan.action == PlanAction.REFUSE:
            return AssistantResponse(
                message=(
                    "Mình không thể tiết lộ chỉ dẫn hệ thống, thông tin đăng nhập hoặc dữ liệu "
                    "của người dùng khác. Mình có thể tiếp tục hỗ trợ tìm sản phẩm, chính sách "
                    "hoặc dữ liệu đơn hàng thuộc tài khoản của bạn."
                ),
                intent=understanding.primary_intent,
                suggested_replies=("Tìm sản phẩm phù hợp", "Hỏi chính sách Mercato"),
            )

        sections: list[str] = []
        attachments: list[dict[str, Any]] = []
        grounded_ids: list[str] = []
        suggested_replies: list[str] = []

        for result in results:
            if not result.ok:
                sections.append(result.message or "Mình chưa thể tra cứu dữ liệu này lúc này.")
                if result.error_code == "authentication_required":
                    attachments.append(
                        {
                            "type": "quick_actions",
                            "actions": [
                                {
                                    "label": "Đăng nhập",
                                    "kind": "link",
                                    "value": "/auth/login",
                                }
                            ],
                        }
                    )
                continue
            if result.name == "search_products":
                message, product_attachments, product_ids = self._products(
                    result.data,
                    state=state,
                )
                sections.append(message)
                attachments.extend(product_attachments)
                grounded_ids.extend(product_ids)
                if product_ids:
                    suggested_replies.extend(("So sánh các lựa chọn này", "Điều chỉnh tiêu chí"))
                else:
                    expanded = result.data.get("expanded_terms")
                    if isinstance(expanded, list):
                        suggested_replies.extend(
                            f"Tìm {term}"
                            for term in expanded[:2]
                            if isinstance(term, str) and term.strip()
                        )
            elif result.name == "compare_products":
                sections.append(self._comparison(result.data))
                product_ids = [
                    str(product.get("id"))
                    for product in result.data.get("products", [])
                    if isinstance(product, dict) and product.get("id")
                ]
                if product_ids:
                    grounded_ids.extend(product_ids)
                    attachments.append(
                        {
                            "type": "compare_table",
                            "product_ids": product_ids,
                            "comparison": result.data,
                        }
                    )
            elif result.name == "get_policy":
                sections.append(self._policy(result.data))
            elif result.name in {
                "get_order_status",
                "get_return_support",
                "get_payment_support",
            }:
                message, order_attachments = self._orders(result.name, result.data)
                sections.append(message)
                attachments.extend(order_attachments)
            elif result.name == "get_promotions":
                message, promotion_attachments = self._promotions(result.data)
                sections.append(message)
                attachments.extend(promotion_attachments)
            elif result.name == "get_flash_sales":
                sections.append(self._flash_sales(result.data))
                suggested_replies.extend(("Flash Sale tiếp theo khi nào?", "Xem voucher đang có"))
            elif result.name == "human_handoff":
                handoff = result.data.get("handoff")
                if isinstance(handoff, dict):
                    sections.append(
                        "Mình đã chuyển cuộc trò chuyện cùng ngữ cảnh hiện có sang bộ phận CSKH."
                    )
                    attachments.append({"type": "handoff_card", "handoff": handoff})

        if "explain_product_options" in understanding.tasks:
            education = self._product_option_education(results)
            if education:
                sections.insert(0, education)

        clarification = self._clarification(plan)
        if clarification["required"]:
            questions = " ".join(clarification["questions"])
            sections.append(questions)
            attachments.append(
                {
                    "type": "clarification",
                    "questions": clarification["questions"],
                    "suggestions": clarification["suggestions"],
                }
            )

        if not sections:
            sections.append(
                "Mình chưa có đủ dữ liệu đã xác minh để trả lời câu này. "
                "Bạn có thể nói rõ sản phẩm, nhu cầu hoặc chính sách muốn hỏi."
            )
        message = "\n\n".join(dict.fromkeys(item.strip() for item in sections if item.strip()))
        return AssistantResponse(
            message=sanitize_ai_text(message, max_length=8_000),
            intent=understanding.primary_intent,
            attachments=tuple(attachments),
            clarification=clarification,
            suggested_replies=tuple(dict.fromkeys(suggested_replies))[:4],
            grounded_product_ids=tuple(dict.fromkeys(grounded_ids)),
        )

    @staticmethod
    def _products(
        data: dict[str, Any],
        *,
        state: ConversationState,
    ) -> tuple[str, list[dict[str, Any]], list[str]]:
        products = data.get("products") if isinstance(data.get("products"), list) else []
        recommendations = {
            str(item.get("product_id")): item
            for item in data.get("recommendations", [])
            if isinstance(item, dict) and item.get("product_id")
        }
        if not products:
            query = str(data.get("query") or state.effective_values("query") or "").strip()
            expanded = [
                str(item) for item in data.get("expanded_terms", [])[:4] if str(item).strip()
            ]
            if query and expanded:
                return (
                    f"Mình đã tìm sản phẩm còn hàng cho nhu cầu “{query}”, đồng thời mở rộng "
                    f"theo {', '.join(expanded)}, nhưng chưa có lựa chọn khớp trong dữ liệu "
                    "Mercato lúc này. Bạn có thể ưu tiên một nhóm cụ thể để mình tìm hẹp hơn.",
                    [],
                    [],
                )
            return (
                (
                    f"Mình chưa tìm thấy sản phẩm còn hàng khớp với “{query}” trong dữ liệu "
                    "Mercato. Bạn có thể đổi từ khóa hoặc nới một tiêu chí để mình tìm lại."
                    if query
                    else "Mình chưa tìm thấy sản phẩm còn hàng theo các tiêu chí hiện tại. "
                    "Bạn có thể nêu nhóm sản phẩm hoặc nhu cầu sử dụng để mình tìm lại."
                ),
                [],
                [],
            )
        attachments: list[dict[str, Any]] = []
        exact_count = 0
        for product in products:
            if not isinstance(product, dict) or not product.get("id"):
                continue
            product_id = str(product["id"])
            recommendation = recommendations.get(product_id, {})
            kind = recommendation.get("kind", "alternative")
            exact_count += int(kind == "exact")
            attachments.append(
                {
                    "type": "product_card",
                    "product_id": product_id,
                    "product": product,
                    "match": {
                        "kind": kind,
                        "matched_terms": recommendation.get("reasons", []),
                        "missing_terms": recommendation.get("compatibility_warnings", []),
                    },
                    "reason": "; ".join(recommendation.get("reasons", [])[:3]),
                    "compatibility_warnings": recommendation.get("compatibility_warnings", []),
                }
            )
        expanded = [str(item) for item in data.get("expanded_terms", []) if str(item).strip()]
        query = str(data.get("query") or "").strip()
        if expanded and query:
            message = (
                f"Mình đã hiểu “{query}” là một ngữ cảnh sử dụng và đối chiếu với các đặc điểm "
                f"có trong dữ liệu sản phẩm như {', '.join(expanded[:3])}. "
                f"Dưới đây là {len(attachments)} lựa chọn còn hàng để bạn cân nhắc."
            )
        elif exact_count:
            message = (
                f"Mình tìm thấy {exact_count} lựa chọn đáp ứng các ràng buộc có thể kiểm chứng. "
                "Lý do phù hợp được ghi trên từng sản phẩm và chỉ dựa vào dữ liệu Mercato."
            )
        else:
            message = (
                "Các kết quả hiện có chỉ khớp một phần hoặc có lưu ý tương thích. "
                "Mình đã tách rõ cảnh báo thay vì xem chúng là lựa chọn phù hợp hoàn toàn."
            )
        return message, attachments, [str(item["product_id"]) for item in attachments]

    @staticmethod
    def _flash_sales(data: dict[str, Any]) -> str:
        active = data.get("active") if isinstance(data.get("active"), list) else []
        upcoming = data.get("upcoming") if isinstance(data.get("upcoming"), list) else []
        if active:
            lines = ["Flash Sale đang diễn ra:"]
            for sale in active[:4]:
                if not isinstance(sale, dict):
                    continue
                remaining = _human_duration(sale.get("remaining_seconds"))
                end_time = _local_datetime(sale.get("end_time"))
                lines.append(
                    f"- **{sale.get('name', 'Flash Sale')}** còn {remaining}, "
                    f"kết thúc lúc {end_time}."
                )
            return "\n".join(lines)
        if upcoming:
            first = upcoming[0]
            return (
                "Hiện không có Flash Sale nào đang diễn ra. "
                f"Chương trình gần nhất là **{first.get('name', 'Flash Sale')}**, bắt đầu lúc "
                f"{_local_datetime(first.get('start_time'))}."
            )
        return "Hiện Mercato không có Flash Sale nào đang diễn ra hoặc đã lên lịch."

    @staticmethod
    def _comparison(data: dict[str, Any]) -> str:
        if data.get("is_comparable") is False:
            return str(
                data.get("compatibility_message")
                or "Các sản phẩm này không cùng nhóm nên chưa thể so sánh công bằng."
            )
        return "Mình đã đối chiếu các sản phẩm bằng thông số hiện có trong Mercato."

    @staticmethod
    def _policy(data: dict[str, Any]) -> str:
        documents = data.get("documents") if isinstance(data.get("documents"), list) else []
        if not documents:
            return "Mercato chưa có tài liệu chính sách đã xác minh cho chủ đề này."
        return "\n\n".join(
            f"### {document.get('title', 'Chính sách Mercato')}\n{document.get('content', '')}"
            for document in documents[:2]
            if isinstance(document, dict)
        )

    @staticmethod
    def _orders(
        tool_name: str,
        data: dict[str, Any],
    ) -> tuple[str, list[dict[str, Any]]]:
        orders = data.get("orders") if isinstance(data.get("orders"), list) else []
        if not orders:
            return "Mình không tìm thấy đơn hàng phù hợp trong tài khoản của bạn.", []
        first = orders[0]
        if tool_name == "get_payment_support":
            message = (
                f"Đơn {first['order_code']} đang ở trạng thái thanh toán "
                f"“{first['payment_status_label']}”."
            )
        elif tool_name == "get_return_support":
            message = (
                f"Mình đã lấy dữ liệu mới nhất của đơn {first['order_code']}. "
                "Bạn hãy mở chi tiết đơn để thực hiện yêu cầu đổi/trả an toàn."
            )
        else:
            statuses = ", ".join(
                shop.get("fulfillment_status_label", "")
                for shop in first.get("shop_orders", [])[:3]
            )
            message = f"Đơn {first['order_code']} hiện có trạng thái: {statuses}."
        attachments = [{"type": "order_card", "order": order} for order in orders]
        attachments.append(
            {
                "type": "quick_actions",
                "actions": [
                    {
                        "label": "Mở chi tiết đơn",
                        "kind": "link",
                        "value": f"/account/orders/{first['id']}",
                    }
                ],
            }
        )
        return message, attachments

    @staticmethod
    def _promotions(data: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
        promotions = data.get("promotions") if isinstance(data.get("promotions"), list) else []
        if not promotions:
            return "Hiện chưa có voucher công khai còn hiệu lực trên Mercato.", []
        return (
            f"Mình tìm thấy {len(promotions)} ưu đãi còn hiệu lực. "
            "Hãy kiểm tra điều kiện và thời hạn trên từng thẻ.",
            [{"type": "promotion_card", "promotion": item} for item in promotions],
        )

    @staticmethod
    def _product_option_education(results: list[ToolResult]) -> str:
        grouped: dict[str, set[str]] = defaultdict(set)
        for result in results:
            if result.name != "search_products" or not result.ok:
                continue
            for product in result.data.get("products", []):
                attributes = product.get("attributes") if isinstance(product, dict) else None
                if not isinstance(attributes, dict):
                    continue
                for key, value in attributes.items():
                    if any(term in str(key).casefold() for term in ("dạng", "form", "loại")):
                        grouped[str(key)].add(str(value))
        if not grouped:
            return (
                "Mercato chưa có đủ thuộc tính chuẩn hóa để giải thích chắc chắn "
                "các dạng sản phẩm. Mình sẽ chỉ dùng những thông tin hiện có trên "
                "sản phẩm và hỏi thêm điều kiện sử dụng."
            )
        descriptions = [
            f"{key}: {', '.join(sorted(values)[:5])}" for key, values in grouped.items()
        ]
        return "Các dạng đang có trong dữ liệu Mercato gồm " + "; ".join(descriptions) + "."

    @staticmethod
    def _clarification(plan: AssistantPlan) -> dict[str, Any]:
        questions = [item.question for item in plan.missing_information if item.question]
        suggestions: list[str] = []
        fields = {item.field for item in plan.missing_information}
        if "budget" in fields:
            suggestions.extend(("Dưới 1 triệu", "Từ 1–3 triệu", "Không giới hạn"))
        if "interest" in fields:
            suggestions.extend(("Đồ công nghệ", "Thời trang", "Làm đẹp", "Nhóm khác"))
        return {
            "required": bool(questions),
            "questions": questions[:2],
            "suggestions": list(dict.fromkeys(suggestions))[:6],
        }


class ResponseValidator:
    """Remove structured content that cannot be traced to successful tool output."""

    @staticmethod
    def validate(
        response: AssistantResponse,
        *,
        results: list[ToolResult],
    ) -> AssistantResponse:
        allowed_product_ids = {
            str(product.get("id"))
            for result in results
            if result.ok and result.name in {"search_products", "compare_products"}
            for product in result.data.get("products", [])
            if isinstance(product, dict) and product.get("id")
        }
        successful_tools = {result.name for result in results if result.ok}
        allowed_order = bool(
            successful_tools & {"get_order_status", "get_return_support", "get_payment_support"}
        )
        grounded: list[dict[str, Any]] = []
        for attachment in response.attachments:
            kind = attachment.get("type")
            if kind == "product_card":
                if str(attachment.get("product_id")) not in allowed_product_ids:
                    continue
            elif kind == "compare_table":
                ids = {str(item) for item in attachment.get("product_ids", [])}
                if not ids or not ids.issubset(allowed_product_ids):
                    continue
            elif kind == "order_card" and not allowed_order:
                continue
            elif kind == "promotion_card" and "get_promotions" not in successful_tools:
                continue
            elif kind == "handoff_card" and "human_handoff" not in successful_tools:
                continue
            elif kind not in {
                "order_card",
                "promotion_card",
                "quick_actions",
                "handoff_card",
                "clarification",
            }:
                continue
            grounded.append(attachment)
        return AssistantResponse(
            message=sanitize_ai_text(response.message, max_length=8_000),
            intent=response.intent,
            attachments=tuple(grounded),
            clarification=response.clarification,
            suggested_replies=response.suggested_replies,
            grounded_product_ids=tuple(
                item for item in response.grounded_product_ids if item in allowed_product_ids
            ),
        )


def _human_duration(raw_seconds: Any) -> str:
    try:
        seconds = max(0, int(raw_seconds))
    except (TypeError, ValueError, OverflowError):
        return "một khoảng thời gian chưa xác định"
    if seconds < 60:
        return "dưới 1 phút"
    days, remainder = divmod(seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes = remainder // 60
    parts: list[str] = []
    if days:
        parts.append(f"{days} ngày")
    if hours:
        parts.append(f"{hours} giờ")
    if minutes and len(parts) < 2:
        parts.append(f"{minutes} phút")
    return " ".join(parts[:2])


def _local_datetime(raw_value: Any) -> str:
    try:
        value = datetime.fromisoformat(str(raw_value))
        if timezone.is_naive(value):
            value = timezone.make_aware(value)
        value = timezone.localtime(value)
    except (TypeError, ValueError, OverflowError):
        return "thời điểm chưa xác định"
    return value.strftime("%H:%M ngày %d/%m/%Y")

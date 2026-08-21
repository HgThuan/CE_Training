import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction

from .models import ChatHandoff, ChatMessage, ChatSession, sanitize_ai_text

ORDER_CODE_RE = re.compile(r"\b(?:S?ORD)-\d{8}-[A-Z0-9]{10}\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class SupportDecision:
    intent: str
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)


def detect_support_intent(text: str) -> SupportDecision | None:
    """Route factual commerce support without asking the language model to infer data."""
    normalized = _normalize(text)
    order_code_match = ORDER_CODE_RE.search(text)
    arguments = {
        "order_code": order_code_match.group(0).upper() if order_code_match else "",
        "limit": 3,
    }

    if any(
        phrase in normalized
        for phrase in (
            "gap nhan vien",
            "noi chuyen voi nhan vien",
            "chuyen nhan vien",
            "tu van vien",
            "nhan vien ho tro",
            "lien he cskh",
            "cham soc khach hang",
        )
    ):
        return SupportDecision(intent="human_handoff")

    if any(
        phrase in normalized
        for phrase in (
            "goi y cho toi",
            "goi y ca nhan",
            "theo so thich",
            "dua tren lich su",
            "phu hop voi toi",
            "mua gi tiep",
        )
    ):
        return SupportDecision(
            intent="personalized_recommendation",
            tool_name="get_personalized_recommendations",
            arguments={"limit": 4},
        )

    promotion_terms = ("ma giam gia", "voucher", "khuyen mai", "free ship", "freeship")
    if any(phrase in normalized for phrase in promotion_terms):
        return SupportDecision(
            intent="promotion_support",
            tool_name="get_active_promotions",
            arguments={"limit": 5},
        )

    return_terms = ("doi tra", "tra hang", "hoan tien", "yeu cau tra", "khieu nai")
    if any(phrase in normalized for phrase in return_terms):
        if any(phrase in normalized for phrase in ("chinh sach", "dieu kien", "quy dinh")):
            return SupportDecision(
                intent="verified_policy",
                tool_name="get_policy",
                arguments={"topic": text},
            )
        return SupportDecision(
            intent="return_support",
            tool_name="get_return_support",
            arguments=arguments,
        )

    payment_terms = ("thanh toan", "giao dich", "vnpay", "cod")
    if any(phrase in normalized for phrase in payment_terms):
        if any(
            phrase in normalized
            for phrase in ("phuong thuc", "ho tro nhung", "chinh sach", "quy dinh")
        ):
            return SupportDecision(
                intent="verified_policy",
                tool_name="get_policy",
                arguments={"topic": text},
            )
        return SupportDecision(
            intent="payment_support",
            tool_name="get_payment_support",
            arguments=arguments,
        )

    if any(
        phrase in normalized
        for phrase in (
            "don hang",
            "theo doi don",
            "lich su mua",
            "giao toi dau",
            "dang giao",
            "bao gio giao",
            "khi nao giao",
        )
    ):
        return SupportDecision(
            intent="order_support",
            tool_name="get_order_status",
            arguments=arguments,
        )
    return None


def render_support_response(intent: str, result: dict[str, Any]) -> str:
    if result.get("code") == "authentication_required":
        return (
            "Để bảo vệ thông tin cá nhân, bạn cần đăng nhập trước khi mình tra cứu "
            "đơn hàng, thanh toán hoặc yêu cầu đổi trả."
        )
    if result.get("error"):
        return str(result.get("message") or "Mình chưa thể tra cứu dữ liệu Mercato lúc này.")

    if intent == "verified_policy":
        documents = result.get("documents") or []
        if not documents:
            return "Mercato chưa có nội dung chính sách đã xác minh cho câu hỏi này."
        return "\n\n".join(f"### {item['title']}\n{item['content']}" for item in documents[:2])

    if intent == "promotion_support":
        promotions = result.get("promotions") or []
        if not promotions:
            return "Hiện chưa có mã giảm giá công khai còn hiệu lực trên Mercato."
        return (
            f"Mình tìm thấy {len(promotions)} ưu đãi đang còn hiệu lực từ hệ thống Mercato. "
            "Bạn xem điều kiện và thời hạn trên từng thẻ bên dưới nhé."
        )

    if intent == "personalized_recommendation":
        products = result.get("products") or []
        if not products:
            return "Mình chưa có đủ tín hiệu hoặc sản phẩm phù hợp để tạo gợi ý cá nhân hóa."
        basis = "lịch sử xem, mua hàng và danh sách yêu thích"
        if not result.get("personalized"):
            basis = "các sản phẩm phổ biến hiện có"
        return (
            f"Mình đã chọn {len(products)} gợi ý dựa trên {basis}. "
            "Giá và tình trạng hiển thị được lấy trực tiếp từ Mercato."
        )

    orders = result.get("orders") or []
    if not orders:
        return str(
            result.get("message") or "Mình không tìm thấy đơn hàng phù hợp trong tài khoản này."
        )
    order = orders[0]
    if intent == "payment_support":
        payment = order.get("payment") or {}
        failure = payment.get("failure_message")
        suffix = f" Lý do hệ thống ghi nhận: {failure}" if failure else ""
        return (
            f"Đơn {order['order_code']} đang ở trạng thái thanh toán "
            f"“{order['payment_status_label']}” bằng {order['payment_method_label']}.{suffix} "
            "Bạn có thể mở chi tiết đơn để tiếp tục thao tác an toàn."
        )
    if intent == "return_support":
        active_returns = [
            item
            for shop in order.get("shop_orders", [])
            for item in shop.get("return_requests", [])
        ]
        eligible = [shop for shop in order.get("shop_orders", []) if shop.get("return_eligible")]
        if active_returns:
            labels = ", ".join(item["status_label"] for item in active_returns[:3])
            return f"Yêu cầu đổi/trả của đơn {order['order_code']} hiện có trạng thái: {labels}."
        if eligible:
            return (
                f"Đơn {order['order_code']} có {len(eligible)} phần đơn còn đủ điều kiện "
                "mở yêu cầu "
                "trả hàng. Hãy mở chi tiết đơn để chọn đúng sản phẩm, số lượng, lý do và chứng cứ."
            )
        return (
            f"Hiện đơn {order['order_code']} chưa có yêu cầu đổi/trả đang xử lý và không có phần "
            "đơn nào đủ điều kiện mở yêu cầu theo dữ liệu hiện tại."
        )

    shop_lines = "; ".join(
        f"{shop['shop_name']}: {shop['fulfillment_status_label']}"
        for shop in order.get("shop_orders", [])[:3]
    )
    prefix = f"Mình đã tra cứu {len(orders)} đơn gần nhất. " if len(orders) > 1 else ""
    return (
        f"{prefix}Đơn {order['order_code']} có trạng thái thanh toán "
        f"“{order['payment_status_label']}”. {shop_lines}. "
        "Mercato chưa có dữ liệu thời gian giao dự kiến riêng; mốc cập nhật trên thẻ là "
        "dữ liệu OMS mới nhất."
    )


@transaction.atomic
def request_human_handoff(session: ChatSession, reason: str) -> ChatHandoff:
    active = (
        session.handoffs.select_for_update()
        .filter(status__in=(ChatHandoff.Status.OPEN, ChatHandoff.Status.ASSIGNED))
        .first()
    )
    if active is not None:
        return active

    messages = list(
        session.messages.filter(
            role__in=(ChatMessage.Role.USER, ChatMessage.Role.ASSISTANT)
        ).order_by("-created_at", "-id")[:20]
    )
    messages.reverse()
    snapshot = [
        {
            "role": message.role,
            "content": sanitize_ai_text(message.content, max_length=1_000),
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]
    summary = sanitize_ai_text(session.history_summary or reason, max_length=2_000)
    handoff = ChatHandoff.objects.create(
        session=session,
        requested_by=session.user,
        reason=sanitize_ai_text(reason, max_length=300),
        conversation_summary=summary,
        context_snapshot=snapshot,
        channel=str(session.context.get("channel", "web"))[:30],
    )
    session.status = ChatSession.Status.ESCALATED
    session.save(update_fields=("status", "updated_at"))
    return handoff


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).replace("đ", "d")
    return " ".join(
        "".join(character if character.isalnum() else " " for character in ascii_value).split()
    )

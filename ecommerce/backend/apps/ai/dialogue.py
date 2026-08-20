import re
from dataclasses import dataclass, field
from typing import Any, Literal

from apps.catalog.models import Category

from .models import ChatMessage, ChatSession
from .product_matching import extract_price_filters, normalize_words

DialogueAction = Literal["delegate", "clarify", "guided_search"]

_APPROXIMATE_BUDGET_RE = re.compile(
    r"\b(?:ngân\s+sách(?:\s+(?:là|khoảng))?|tầm|khoảng)\s*"
    r"(?P<number>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>triệu|tr|nghìn|ngàn|k|vnd|đ|đồng)?\b",
    re.IGNORECASE,
)
_STANDALONE_BUDGET_RE = re.compile(
    r"^\s*(?P<number>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>triệu|tr|nghìn|ngàn|k|vnd|đ|đồng)\s*[.!]?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_BUDGET_RANGE_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:triệu|tr|nghìn|ngàn|k)?\s*"
    r"(?:-|–|đến|tới)\s*"
    r"(?P<number>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>triệu|tr|nghìn|ngàn|k|vnd|đ|đồng)\b",
    re.IGNORECASE,
)
_INTEREST_RE = re.compile(
    r"\b(?:thích|đam\s+mê|quan\s+tâm(?:\s+đến)?)\s+"
    r"(?P<interest>.+?)"
    r"(?=\s*[,.;]|\s+(?:với\s+)?(?:ngân\s+sách|tầm|khoảng)\b|$)",
    re.IGNORECASE,
)
_PURPOSE_RE = re.compile(
    r"\b(?:để|phục\s+vụ|dùng\s+cho)\s+"
    r"(?P<purpose>.+?)"
    r"(?=\s*[,.;]|\s+(?:với\s+)?(?:ngân\s+sách|tầm|khoảng)\b|$)",
    re.IGNORECASE,
)

_CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "am thanh": ("am thanh", "tai nghe", "loa", "earbuds", "headphone"),
    "phu kien": ("phu kien", "sac du phong", "cu sac", "op lung", "cap sac"),
    "thiet bi deo": ("thiet bi deo", "dong ho", "smartwatch", "vong deo"),
    "dien thoai": ("dien thoai", "smartphone"),
    "may tinh bang": ("may tinh bang", "tablet"),
    "laptop": ("laptop", "may tinh xach tay"),
    "do the thao": ("do the thao", "dung cu the thao"),
    "quan ao da bong": ("quan ao da bong", "ao bong da", "do da bong"),
    "quan ao": ("quan ao", "thoi trang"),
}

_INTEREST_CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "cong nghe": ("am thanh", "phu kien", "thiet bi deo"),
    "am nhac": ("am thanh",),
    "the thao": ("do the thao", "quan ao da bong", "thiet bi deo"),
    "bong da": ("quan ao da bong", "do the thao"),
    "thoi trang": ("quan ao", "phu kien"),
    "chup anh": ("dien thoai", "phu kien"),
    "hoc tap": ("laptop", "may tinh bang"),
    "lam viec": ("laptop", "may tinh bang"),
}


@dataclass(frozen=True, slots=True)
class ShoppingSlots:
    occasion: str = ""
    interest: str = ""
    category: str = ""
    product_query: str = ""
    max_price: int | None = None
    flexible_budget: bool = False


@dataclass(frozen=True, slots=True)
class DialogueDecision:
    action: DialogueAction
    intent: str = "general"
    response: str = ""
    effective_need: str = ""
    search_need: str = ""
    search_arguments: dict[str, Any] = field(default_factory=dict)


class ShoppingDialogueManager:
    """Collect deterministic shopping constraints before delegating to catalog search."""

    MAX_USER_MESSAGES = 8

    def decide(self, session: ChatSession, current_text: str) -> DialogueDecision:
        if self._should_bypass_guided_flow(current_text) or self._cancels_guided_flow(current_text):
            return DialogueDecision(action="delegate")

        messages = list(
            session.messages.filter(
                role__in=(ChatMessage.Role.USER, ChatMessage.Role.ASSISTANT)
            ).order_by("-created_at", "-id")[: self.MAX_USER_MESSAGES * 2]
        )
        messages.reverse()
        guided_start = self._active_guided_start(messages)
        if guided_start is None:
            return DialogueDecision(action="delegate")

        active_messages = messages[guided_start:]
        is_gift = _is_gift_intent(active_messages[0].content)
        intent = "gift_advice" if is_gift else "shopping_advice"
        user_texts = [
            message.content for message in active_messages if message.role == ChatMessage.Role.USER
        ]
        categories = list(
            Category.objects.filter(is_active=True, is_deleted=False)
            .order_by("sort_order", "name", "id")
            .values_list("name", flat=True)
        )
        slots = self._extract_slots(user_texts, current_text, categories, is_gift=is_gift)
        response = self._clarification(slots, categories, is_gift=is_gift)
        if response:
            return DialogueDecision(
                action="clarify",
                intent=intent,
                response=response,
            )

        budget_text = (
            "ngân sách linh hoạt"
            if slots.flexible_budget
            else f"ngân sách không quá {self._format_price(slots.max_price)}"
        )
        preference_text = f", ưu tiên sở thích {slots.interest}" if slots.interest else ""
        selection_text = f"nhóm {slots.category}"
        if _normalize(slots.product_query) != _normalize(slots.category):
            selection_text = f"{slots.product_query} thuộc nhóm {slots.category}"
        if is_gift:
            occasion_text = f" {slots.occasion}" if slots.occasion else ""
            effective_need = (
                f"Tìm quà{occasion_text}: {selection_text}{preference_text}, {budget_text}."
            )
        else:
            effective_need = f"Tìm sản phẩm {selection_text}{preference_text}, {budget_text}."
        search_need = slots.product_query
        search_arguments: dict[str, Any] = {
            "query": slots.product_query,
            "category": slots.category,
            "limit": 4,
        }
        if slots.max_price is not None:
            search_need += f" dưới {slots.max_price} đồng"
            search_arguments["max_price"] = slots.max_price
        return DialogueDecision(
            action="guided_search",
            intent=intent,
            effective_need=effective_need,
            search_need=search_need,
            search_arguments=search_arguments,
        )

    @staticmethod
    def _active_guided_start(messages: list[ChatMessage]) -> int | None:
        start_at = 0
        for index, message in enumerate(messages):
            if message.role != ChatMessage.Role.ASSISTANT:
                continue
            if any(
                attachment.get("type") == "product_card"
                for attachment in (message.attachments or [])
                if isinstance(attachment, dict)
            ):
                start_at = index + 1

        for index in range(start_at, len(messages)):
            message = messages[index]
            if message.role == ChatMessage.Role.USER and _is_guided_advice_intent(message.content):
                return index
        return None

    @staticmethod
    def _should_bypass_guided_flow(current_text: str) -> bool:
        normalized = _normalize(current_text)
        bypass_phrases = (
            "chinh sach",
            "giao hang",
            "van chuyen",
            "doi tra",
            "tra hang",
            "hoan tien",
            "thanh toan",
            "bao hanh",
            "so sanh",
        )
        return any(phrase in normalized for phrase in bypass_phrases)

    @staticmethod
    def _cancels_guided_flow(current_text: str) -> bool:
        normalized = _normalize(current_text)
        return any(
            phrase in normalized
            for phrase in (
                "khong mua qua nua",
                "khong muon mua",
                "chua muon mua",
                "bo qua nhu cau nay",
                "huy nhu cau nay",
                "doi sang nhu cau khac",
            )
        )

    def _extract_slots(
        self,
        user_texts: list[str],
        current_text: str,
        categories: list[str],
        *,
        is_gift: bool,
    ) -> ShoppingSlots:
        transcript = "\n".join(user_texts)
        category, product_query = self._match_category(user_texts, categories)
        interest = self._extract_interest(transcript)
        if not interest and not is_gift:
            interest = self._extract_purpose(transcript)
        max_price, flexible_budget = self._latest_budget(user_texts)

        normalized_current = _normalize(current_text)
        if (
            not interest
            and len(user_texts) > 1
            and not category
            and max_price is None
            and 0 < len(normalized_current.split()) <= 6
            and not any(character.isdigit() for character in current_text)
            and normalized_current not in {"khong biet", "chua biet", "tuy ban"}
        ):
            interest = current_text.strip(" ,.;:!?-")

        return ShoppingSlots(
            occasion=self._extract_occasion(transcript),
            interest=interest,
            category=category,
            product_query=product_query,
            max_price=max_price,
            flexible_budget=flexible_budget,
        )

    @staticmethod
    def _match_category(user_texts: list[str], categories: list[str]) -> tuple[str, str]:
        normalized_categories = sorted(
            ((_normalize(category), category) for category in categories),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        for user_text in reversed(user_texts):
            padded_text = f" {_normalize(user_text)} "
            for normalized_category, category in normalized_categories:
                if normalized_category and f" {normalized_category} " in padded_text:
                    return category, category

            for canonical, aliases in _CATEGORY_ALIASES.items():
                matched_alias = next(
                    (alias for alias in aliases if f" {alias} " in padded_text),
                    "",
                )
                if not matched_alias:
                    continue
                for normalized_category, category in normalized_categories:
                    if canonical in normalized_category or normalized_category in canonical:
                        return category, matched_alias
        return "", ""

    @classmethod
    def _latest_budget(cls, user_texts: list[str]) -> tuple[int | None, bool]:
        flexible_phrases = (
            "khong gioi han ngan sach",
            "ngan sach linh hoat",
            "gia nao cung duoc",
        )
        for user_text in reversed(user_texts):
            normalized = _normalize(user_text)
            if any(phrase in normalized for phrase in flexible_phrases):
                return None, True
            max_price = extract_price_filters(user_text).get("max_price")
            if max_price is None:
                max_price = cls._extract_approximate_budget(user_text)
            if max_price is not None:
                return max_price, False
        return None, False

    @staticmethod
    def _extract_interest(transcript: str) -> str:
        matches = list(_INTEREST_RE.finditer(transcript))
        if not matches:
            return ""
        return " ".join(matches[-1].group("interest").split())[:100]

    @staticmethod
    def _extract_occasion(transcript: str) -> str:
        normalized = _normalize(transcript)
        occasions = (
            ("sinh nhat", "sinh nhật"),
            ("tan gia", "tân gia"),
            ("tot nghiep", "tốt nghiệp"),
            ("ky niem", "kỷ niệm"),
            ("dam cuoi", "đám cưới"),
            ("qua cuoi", "đám cưới"),
            ("giang sinh", "Giáng sinh"),
            ("noel", "Giáng sinh"),
            ("20 10", "20/10"),
            ("8 3", "8/3"),
        )
        for phrase, label in occasions:
            if phrase in normalized:
                return label
        return ""

    @staticmethod
    def _extract_purpose(transcript: str) -> str:
        matches = list(_PURPOSE_RE.finditer(transcript))
        if not matches:
            return ""
        purpose = " ".join(matches[-1].group("purpose").split())[:100]
        if _normalize(purpose) in {"toi", "minh", "em"}:
            return ""
        return purpose

    @staticmethod
    def _extract_approximate_budget(transcript: str) -> int | None:
        matches = list(_BUDGET_RANGE_RE.finditer(transcript))
        if not matches:
            matches = list(_APPROXIMATE_BUDGET_RE.finditer(transcript))
        if not matches:
            matches = list(_STANDALONE_BUDGET_RE.finditer(transcript))
        if not matches:
            return None
        match = matches[-1]
        number = float(match.group("number").replace(",", "."))
        unit = (match.group("unit") or "").casefold()
        if unit in {"triệu", "tr"}:
            number *= 1_000_000
        elif unit in {"nghìn", "ngàn", "k"}:
            number *= 1_000
        return max(0, int(number))

    def _clarification(
        self,
        slots: ShoppingSlots,
        categories: list[str],
        *,
        is_gift: bool,
    ) -> str:
        has_budget = slots.max_price is not None or slots.flexible_budget
        if not slots.category and not slots.interest and not has_budget:
            if is_gift:
                occasion_text = f" {slots.occasion}" if slots.occasion else " phù hợp"
                return (
                    f"Được chứ, mình sẽ giúp bạn chọn quà{occasion_text}. Cho mình biết thêm "
                    "hai điều nhé:\n\n"
                    "- Bạn ấy thích gì, hoặc bạn muốn ưu tiên nhóm quà nào?\n"
                    "- Ngân sách dự kiến khoảng bao nhiêu?"
                )
            return (
                "Được chứ, để tư vấn sát hơn, bạn cho mình biết hai điều nhé:\n\n"
                "- Bạn cần sản phẩm cho mục đích gì, hoặc muốn ưu tiên nhóm nào?\n"
                "- Ngân sách dự kiến khoảng bao nhiêu?"
            )

        questions: list[str] = []
        if not slots.category:
            if slots.interest:
                suggestions = self._category_suggestions(slots.interest, categories)
                if suggestions:
                    questions.append(
                        "Bạn muốn ưu tiên nhóm nào: "
                        + ", ".join(suggestions[:-1])
                        + (" hay " if len(suggestions) > 1 else "")
                        + suggestions[-1]
                        + "?"
                    )
                else:
                    questions.append("Bạn muốn ưu tiên nhóm sản phẩm nào?")
            else:
                questions.append(
                    "Người nhận thích gì, hoặc bạn muốn chọn nhóm sản phẩm nào?"
                    if is_gift
                    else "Bạn cần sản phẩm cho mục đích gì, hoặc muốn chọn nhóm nào?"
                )
        if not has_budget:
            questions.append("Ngân sách dự kiến khoảng bao nhiêu?")

        if not questions:
            return ""

        known_parts: list[str] = []
        if slots.interest:
            known_parts.append(f"sở thích {slots.interest}")
        if slots.category:
            known_parts.append(f"nhóm {slots.category}")
        if slots.max_price is not None:
            known_parts.append(f"ngân sách khoảng {self._format_price(slots.max_price)}")
        elif slots.flexible_budget:
            known_parts.append("ngân sách linh hoạt")

        acknowledgement = "Mình đã ghi nhận " + ", ".join(known_parts) + ". " if known_parts else ""
        return acknowledgement + " ".join(questions[:2])

    @staticmethod
    def _category_suggestions(interest: str, categories: list[str]) -> list[str]:
        normalized_interest = _normalize(interest)
        normalized_categories = [(_normalize(category), category) for category in categories]
        desired: tuple[str, ...] = ()
        for interest_phrase, category_names in _INTEREST_CATEGORY_HINTS.items():
            if interest_phrase in normalized_interest:
                desired = category_names
                break

        suggestions: list[str] = []
        for desired_name in desired:
            for normalized_category, category in normalized_categories:
                if desired_name in normalized_category or normalized_category in desired_name:
                    suggestions.append(category)
                    break
        if suggestions:
            return list(dict.fromkeys(suggestions))[:3]
        return categories[:3]

    @staticmethod
    def _format_price(value: int | None) -> str:
        if value is None:
            return ""
        return f"{value:,}".replace(",", ".") + " đ"


def _normalize(value: str) -> str:
    return " ".join(normalize_words(value))


def _is_gift_intent(value: str) -> bool:
    normalized = _normalize(value)
    words = set(normalized.split())
    return "qua" in words and bool(words.intersection({"mua", "tang", "sinh", "nhat"}))


def _is_guided_advice_intent(value: str) -> bool:
    if _is_gift_intent(value):
        return True
    normalized = _normalize(value)
    return any(
        phrase in normalized
        for phrase in (
            "tu van",
            "goi y",
            "nen mua",
            "khong biet mua",
            "muon mua",
        )
    )

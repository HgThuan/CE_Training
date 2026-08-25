from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

NO_PREFERENCE = "no_preference"


@dataclass(frozen=True, slots=True)
class SlotDefinition:
    name: str
    value_type: str
    aliases: tuple[str, ...]


# One declarative registry is shared by deterministic extraction and dialogue
# state. Adding another numeric/choice slot does not require another special
# branch for open answers.
SLOT_DEFINITIONS = (
    SlotDefinition("budget", "numeric", ("ngân sách", "mức giá", "giá")),
    SlotDefinition("brand", "choice", ("thương hiệu", "hãng")),
    SlotDefinition("color", "choice", ("màu sắc", "màu")),
    SlotDefinition("size", "choice", ("kích thước", "size", "cỡ")),
    SlotDefinition("quantity", "numeric", ("số lượng",)),
    SlotDefinition("rating", "numeric", ("đánh giá", "số sao")),
    SlotDefinition(
        "product_type",
        "choice",
        ("loại sản phẩm", "nhóm sản phẩm", "dòng sản phẩm"),
    ),
    SlotDefinition("interest", "choice", ("sở thích", "mối quan tâm")),
    SlotDefinition("usage", "choice", ("mục đích", "nhu cầu sử dụng")),
)

_OPEN_VALUE_PATTERNS = (
    "không giới hạn",
    "không quan trọng",
    "không yêu cầu",
    "bao nhiêu cũng được",
    "nào cũng được",
    "bất kỳ",
    "tùy",
    "tuỳ",
)
_NUMERIC_OPEN_PATTERNS = ("không giới hạn", "bao nhiêu cũng được")


def extract_no_preferences(
    text: str,
    *,
    pending_slots: Iterable[str] = (),
) -> dict[str, str]:
    """Extract every explicitly unconstrained numeric/choice slot in a turn."""
    normalized = _normalize(text)
    if not _contains_open_value(normalized):
        return {}

    completed: dict[str, str] = {}
    clauses = [item.strip() for item in re.split(r"[,;.!?]+", normalized) if item.strip()]
    for clause in clauses or [normalized]:
        if not _contains_open_value(clause):
            continue
        for definition in SLOT_DEFINITIONS:
            if any(_contains_term(clause, alias) for alias in definition.aliases):
                completed[definition.name] = NO_PREFERENCE

    if completed:
        return completed

    pending_definitions = [
        definition for definition in SLOT_DEFINITIONS if definition.name in set(pending_slots)
    ]
    if any(_contains_term(normalized, pattern) for pattern in _NUMERIC_OPEN_PATTERNS):
        numeric_pending = [item for item in pending_definitions if item.value_type == "numeric"]
        if numeric_pending:
            return {item.name: NO_PREFERENCE for item in numeric_pending}
    if len(pending_definitions) == 1:
        return {pending_definitions[0].name: NO_PREFERENCE}
    return {}


def is_no_preference(value: object) -> bool:
    return str(value or "").strip().casefold() == NO_PREFERENCE


def slot_aliases() -> tuple[str, ...]:
    return tuple(alias for definition in SLOT_DEFINITIONS for alias in definition.aliases)


def _contains_open_value(value: str) -> bool:
    return any(_contains_term(value, pattern) for pattern in _OPEN_VALUE_PATTERNS)


def _contains_term(value: str, term: str) -> bool:
    normalized_term = _normalize(term)
    return bool(normalized_term and re.search(rf"(?<!\w){re.escape(normalized_term)}(?!\w)", value))


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", str(value).casefold())
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).replace("đ", "d")
    return " ".join(
        "".join(character if character.isalnum() else " " for character in ascii_value).split()
    )

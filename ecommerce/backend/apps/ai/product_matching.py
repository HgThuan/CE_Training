import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

STOP_WORDS = {
    "anh",
    "ban",
    "can",
    "cho",
    "co",
    "cua",
    "dang",
    "de",
    "em",
    "giup",
    "la",
    "loai",
    "minh",
    "mot",
    "mua",
    "muon",
    "nao",
    "nguoi",
    "nhu",
    "san",
    "pham",
    "phu",
    "hop",
    "quan",
    "tam",
    "tim",
    "toi",
    "tu",
    "van",
    "xin",
}

# Context words influence ranking but are not hard product capabilities.
SOFT_PREFERENCE_WORDS = {
    "ben",
    "dep",
    "gia",
    "hang",
    "hoc",
    "ngay",
    "re",
    "sinh",
    "tap",
    "tot",
    "van",
    "vien",
    "phong",
}

PRICE_EXPRESSION_RE = re.compile(
    r"\b(?:duoi|tren|tu|toi\s+da|khong\s+qua|it\s+nhat)?\s*"
    r"\d+(?:[.,]\d+)?\s*(?:trieu|tr|nghin|ngan|k|vnd|d|dong)?\b"
)
RAW_PRICE_RE = re.compile(
    r"\b(?P<operator>dưới|không\s+quá|tối\s+đa|trên|từ|ít\s+nhất|tối\s+thiểu)\s+"
    r"(?P<number>\d+(?:[.,]\d+)?)\s*(?P<unit>triệu|tr|k|nghìn)?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ProductMatch:
    product_id: str
    kind: str
    matched_terms: tuple[str, ...]
    missing_terms: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_words(value: str) -> list[str]:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).replace("đ", "d")
    normalized = "".join(character if character.isalnum() else " " for character in ascii_value)
    return normalized.split()


def assess_product_matches(
    *,
    user_need: str,
    products: Iterable[Any],
    attribute_text_by_product: Mapping[str, Iterable[str]] | None = None,
    price_range_by_product: Mapping[str, tuple[Any, Any]] | None = None,
) -> list[ProductMatch]:
    """Classify candidates using only catalog text that can be inspected and cited."""
    normalized_need = " ".join(normalize_words(user_need))
    without_price = PRICE_EXPRESSION_RE.sub(" ", normalized_need)
    need_terms = _unique(
        term
        for term in without_price.split()
        if len(term) >= 2 and term not in STOP_WORDS and term not in SOFT_PREFERENCE_WORDS
    )
    attribute_text_by_product = attribute_text_by_product or {}
    price_range_by_product = price_range_by_product or {}
    price_filters = extract_price_filters(user_need)
    matches: list[ProductMatch] = []

    for product in products:
        product_id = str(product.pk)
        document_parts = [
            product.name,
            product.short_description or "",
            product.description or "",
            getattr(product.category, "name", ""),
            getattr(product.brand, "name", "") if product.brand_id else "",
            *attribute_text_by_product.get(product_id, ()),
        ]
        document_terms = set(normalize_words(" ".join(document_parts)))
        matched_terms = tuple(term for term in need_terms if term in document_terms)
        missing_terms = [term for term in need_terms if term not in document_terms]
        minimum_price, maximum_price = price_range_by_product.get(
            product_id,
            (getattr(product, "min_price", None), getattr(product, "max_price", None)),
        )
        if price_filters.get("max_price") is not None and minimum_price is not None:
            if Decimal(str(minimum_price)) > price_filters["max_price"]:
                missing_terms.append(f"budget_max:{price_filters['max_price']}")
        if price_filters.get("min_price") is not None and maximum_price is not None:
            if Decimal(str(maximum_price)) < price_filters["min_price"]:
                missing_terms.append(f"budget_min:{price_filters['min_price']}")
        kind = "exact" if need_terms and not missing_terms else "alternative"
        matches.append(
            ProductMatch(
                product_id=product_id,
                kind=kind,
                matched_terms=matched_terms,
                missing_terms=tuple(missing_terms),
            )
        )
    return matches


def humanize_terms(terms: Iterable[str]) -> list[str]:
    return [term.replace("_", " ") for term in _unique(terms)]


def extract_price_filters(value: str) -> dict[str, int]:
    filters: dict[str, int] = {}
    for match in RAW_PRICE_RE.finditer(value):
        operator = " ".join(match.group("operator").casefold().split())
        number = Decimal(match.group("number").replace(",", "."))
        unit = (match.group("unit") or "").casefold()
        if unit in {"triệu", "tr"}:
            number *= Decimal("1000000")
        elif unit in {"k", "nghìn"}:
            number *= Decimal("1000")
        key = "max_price" if operator in {"dưới", "không quá", "tối đa"} else "min_price"
        filters[key] = max(0, int(number))
    return filters


def remove_price_constraints(value: str) -> str:
    return RAW_PRICE_RE.sub(" ", value)


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))

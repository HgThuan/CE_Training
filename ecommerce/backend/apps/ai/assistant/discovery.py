from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiscoveryScenario:
    label: str
    phrases: tuple[str, ...]
    search_terms: tuple[str, ...]


# These expansions are deliberately reviewable. They are search hints, not claims
# that every matching product is suitable for every customer in the scenario.
DISCOVERY_SCENARIOS = (
    DiscoveryScenario(
        label="đi biển",
        phrases=("đi biển", "du lịch biển", "bãi biển"),
        search_terms=(
            "kem chống nắng",
            "chống nắng",
            "chống nước",
            "hoạt động ngoài trời",
            "du lịch",
        ),
    ),
    DiscoveryScenario(
        label="du lịch",
        phrases=("đi du lịch", "du lịch", "đi xa"),
        search_terms=("pin sạc dự phòng", "di động", "nhỏ gọn", "du lịch"),
    ),
    DiscoveryScenario(
        label="học tập",
        phrases=("đi học", "học tập", "sinh viên", "học online"),
        search_terms=("học tập", "sinh viên", "học trực tuyến", "pin lâu"),
    ),
    DiscoveryScenario(
        label="làm việc",
        phrases=("đi làm", "làm việc", "văn phòng", "công sở"),
        search_terms=("văn phòng", "công việc", "công thái học", "di chuyển"),
    ),
    DiscoveryScenario(
        label="tập luyện",
        phrases=("tập gym", "tập luyện", "chạy bộ", "thể thao"),
        search_terms=("chạy bộ", "tập gym", "thể thao", "chống nước"),
    ),
)


def match_discovery_scenario(value: str) -> DiscoveryScenario | None:
    normalized = _normalize(value)
    return next(
        (
            scenario
            for scenario in DISCOVERY_SCENARIOS
            if any(_contains_phrase(normalized, phrase) for phrase in scenario.phrases)
        ),
        None,
    )


def search_terms_for_usage(value: object) -> tuple[str, ...]:
    normalized = _normalize(str(value or ""))
    scenario = next(
        (item for item in DISCOVERY_SCENARIOS if _contains_phrase(normalized, item.label)),
        None,
    )
    return scenario.search_terms if scenario else ()


def _contains_phrase(normalized_value: str, phrase: str) -> bool:
    normalized_phrase = _normalize(phrase)
    return f" {normalized_phrase} " in f" {normalized_value} "


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).replace("đ", "d")
    return " ".join(
        "".join(character if character.isalnum() else " " for character in ascii_value).split()
    )

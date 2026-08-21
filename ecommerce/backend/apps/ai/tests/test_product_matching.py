from types import SimpleNamespace
from uuid import uuid4

from apps.ai.product_matching import assess_product_matches, extract_price_filters


def product(
    *,
    name: str,
    description: str = "",
    category: str = "",
    min_price=None,
    max_price=None,
):
    return SimpleNamespace(
        pk=uuid4(),
        name=name,
        short_description="",
        description=description,
        category=SimpleNamespace(name=category),
        brand=None,
        brand_id=None,
        min_price=min_price,
        max_price=max_price,
    )


def test_accessibility_requirements_without_catalog_evidence_are_alternatives():
    watch = product(
        name="Đồng hồ Samsung Galaxy Watch6",
        description="Theo dõi vận động và nhịp tim.",
        category="Thiết bị đeo",
    )

    match = assess_product_matches(
        user_need="Tôi cần đồng hồ chữ nổi Braille cho người khiếm thị",
        products=[watch],
    )[0]

    assert match.kind == "alternative"
    assert {"braille", "khiem", "thi"}.issubset(match.missing_terms)


def test_soft_usage_context_does_not_turn_a_matching_product_into_an_alternative():
    laptop = product(name="Laptop Lenovo IdeaPad", category="Laptop")

    match = assess_product_matches(
        user_need="Tìm laptop học tập cho sinh viên dưới 20 triệu",
        products=[laptop],
    )[0]

    assert match.kind == "exact"
    assert match.missing_terms == ()


def test_hard_feature_must_be_present_in_catalog_text_or_attributes():
    watch = product(name="Đồng hồ thông minh", category="Thiết bị đeo")

    without_evidence = assess_product_matches(
        user_need="Đồng hồ có cảnh báo té ngã",
        products=[watch],
    )[0]
    with_evidence = assess_product_matches(
        user_need="Đồng hồ có cảnh báo té ngã",
        products=[watch],
        attribute_text_by_product={str(watch.pk): ["Cảnh báo té ngã"]},
    )[0]

    assert without_evidence.kind == "alternative"
    assert with_evidence.kind == "exact"


def test_price_constraints_are_extracted_for_deterministic_fallback_search():
    assert extract_price_filters("Laptop từ 12 triệu đến tối đa 20 triệu") == {
        "min_price": 12_000_000,
        "max_price": 20_000_000,
    }


def test_product_outside_requested_budget_is_only_an_alternative():
    laptop = product(
        name="Laptop Dell XPS",
        category="Laptop",
        min_price="25990000",
        max_price="32990000",
    )

    match = assess_product_matches(
        user_need="Tìm laptop học tập dưới 20 triệu",
        products=[laptop],
    )[0]

    assert match.kind == "alternative"
    assert "budget_max:20000000" in match.missing_terms

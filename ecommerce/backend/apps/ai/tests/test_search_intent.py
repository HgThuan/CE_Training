from apps.ai.search_intent import SearchIntentParser


def test_vague_vietnamese_gift_query_extracts_semantic_slots_and_categories():
    intent = SearchIntentParser.parse(
        query="Tìm quà sinh nhật cho bạn gái dưới 2 triệu",
        raw_intent={
            "keywords": ["quà sinh nhật"],
            "filters": {"price_max": 2_000_000},
            "slots": {},
            "confidence": 0.4,
        },
        validated_filters={"price_max": 2_000_000, "q": "quà sinh nhật"},
    )

    assert intent.occasion == "birthday"
    assert intent.recipient == "girlfriend"
    assert {"mỹ phẩm", "trang sức", "nước hoa"}.issubset(intent.category_hints)
    assert intent.filters == {"price_max": 2_000_000}
    assert intent.confidence >= 0.75


def test_controlled_explanation_uses_only_normalized_slots_not_model_prose():
    intent = SearchIntentParser.parse(
        query="áo xanh dưới 500k",
        raw_intent={
            "keywords": ["áo"],
            "filters": {"price_max": 500_000},
            "slots": {"attributes": {"màu": ["xanh"]}},
            "explanation": "Sản phẩm này chắc chắn làm từ lụa cao cấp.",
        },
        validated_filters={"price_max": 500_000},
    )

    explanation = SearchIntentParser.controlled_explanation(intent)

    assert "500,000 ₫" in explanation
    assert "xanh" in explanation
    assert "lụa" not in explanation

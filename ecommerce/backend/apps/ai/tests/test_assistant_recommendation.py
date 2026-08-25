import pytest
from django.utils import timezone

from apps.account.models import User
from apps.account.tests.factories import UserFactory
from apps.ai.assistant.planner import AssistantPlanner
from apps.ai.assistant.recommendation import GroundedRecommendationEngine
from apps.ai.assistant.responses import GroundedResponseComposer, ResponseValidator
from apps.ai.assistant.schemas import AssistantPlan, QueryUnderstanding, ToolResult
from apps.ai.assistant.state import ConversationState, ConversationStateRepository
from apps.ai.assistant.tooling import AssistantToolRegistry, ToolContext
from apps.ai.assistant.understanding import QueryUnderstandingService
from apps.ai.models import ChatSession
from apps.ai.services import AIResult
from apps.catalog.tests.factories import BrandFactory, CategoryFactory
from apps.inventory.tests.factories import InventoryBalanceFactory
from apps.product.models import Product
from apps.product.selectors import ProductSelector, SearchSelector
from apps.product.tests.factories import ProductFactory, ProductVariantFactory
from apps.promotion.models import FlashSale


class OfflineAIService:
    def generate_text(self, **kwargs):
        return AIResult(
            text="",
            ai_used=False,
            fallback_used=True,
            cached=False,
            model_name="offline",
        )


def _state(**values):
    return ConversationState(
        constraints={
            key: {"value": value, "source": "user", "turn": 1, "confidence": 1}
            for key, value in values.items()
        }
    )


def test_product_incompatibility_is_explicit_and_ranked_last(settings):
    settings.AI_ASSISTANT_RANK_CATEGORY_WEIGHT = 0.3
    settings.AI_ASSISTANT_RANK_BRAND_WEIGHT = 0.2
    settings.AI_ASSISTANT_RANK_PRICE_WEIGHT = 0.2
    settings.AI_ASSISTANT_RANK_PREFERENCE_WEIGHT = 0.1
    settings.AI_ASSISTANT_RANK_RATING_WEIGHT = 0.1
    settings.AI_ASSISTANT_RANK_STOCK_WEIGHT = 0.1
    settings.AI_ASSISTANT_RANK_INCOMPATIBILITY_PENALTY = 0.8
    state = _state(unavailable_equipment=["máy xay"])
    products = [
        {
            "id": "whole-bean",
            "name": "Cà phê nguyên hạt",
            "attributes": {"Yêu cầu máy xay": "Có"},
            "stock_status": "in_stock",
        },
        {
            "id": "ground",
            "name": "Cà phê bột",
            "attributes": {"Yêu cầu máy xay": "Không"},
            "stock_status": "in_stock",
        },
    ]

    ranked = GroundedRecommendationEngine().rank(products=products, state=state)

    assert ranked[0]["product"]["id"] == "ground"
    assert "máy xay" in ranked[1]["compatibility_warnings"][0]


def test_empty_tool_result_never_creates_fake_product():
    understanding = QueryUnderstanding(tasks=("search_products",))
    result = ToolResult(
        name="search_products",
        ok=True,
        data={"products": [], "recommendations": []},
    )
    response = GroundedResponseComposer().compose(
        understanding=understanding,
        plan=AssistantPlan(action="search"),
        state=ConversationState(),
        results=[result],
    )
    validated = ResponseValidator.validate(response, results=[result])

    assert "chưa tìm thấy" in validated.message
    assert validated.attachments == ()
    assert validated.grounded_product_ids == ()


def test_empty_context_search_offers_grounded_narrowing_actions():
    state = _state(query="đi biển")
    result = ToolResult(
        name="search_products",
        ok=True,
        data={
            "products": [],
            "recommendations": [],
            "query": "đi biển",
            "expanded_terms": ["kem chống nắng", "chống nước"],
        },
    )

    response = GroundedResponseComposer().compose(
        understanding=QueryUnderstanding(tasks=("recommend_products",)),
        plan=AssistantPlan(action="search"),
        state=state,
        results=[result],
    )

    assert "mở rộng theo kem chống nắng, chống nước" in response.message
    assert response.suggested_replies == ("Tìm kem chống nắng", "Tìm chống nước")


def test_validator_removes_ungrounded_product_cards():
    result = ToolResult(
        name="search_products",
        ok=True,
        data={"products": [{"id": "real"}]},
    )
    response = GroundedResponseComposer().compose(
        understanding=QueryUnderstanding(tasks=("search_products",)),
        plan=AssistantPlan(action="search"),
        state=ConversationState(),
        results=[result],
    )
    tampered = response.__class__(
        message=response.message,
        intent=response.intent,
        attachments=(*response.attachments, {"type": "product_card", "product_id": "fake"}),
        grounded_product_ids=(*response.grounded_product_ids, "fake"),
    )

    validated = ResponseValidator.validate(tampered, results=[result])

    assert {item["product_id"] for item in validated.attachments} == {"real"}
    assert validated.grounded_product_ids == ("real",)


@pytest.mark.django_db
def test_search_tool_enforces_brand_price_and_stock_constraints(settings):
    settings.AI_ASSISTANT_RESULT_LIMIT = 4
    category = CategoryFactory(name="Điện thoại", slug="dien-thoai")
    samsung = BrandFactory(name="Samsung", slug="samsung")
    apple = BrandFactory(name="Apple", slug="apple")
    matching = ProductFactory(
        category=category,
        brand=samsung,
        name="Điện thoại Samsung Galaxy",
        status=Product.Status.APPROVED,
        min_price=12_000_000,
        max_price=12_000_000,
    )
    too_expensive = ProductFactory(
        category=category,
        brand=samsung,
        name="Điện thoại Samsung Ultra",
        status=Product.Status.APPROVED,
        min_price=25_000_000,
        max_price=25_000_000,
    )
    wrong_brand = ProductFactory(
        category=category,
        brand=apple,
        name="Điện thoại Samsung compatible Apple",
        status=Product.Status.APPROVED,
        min_price=10_000_000,
        max_price=10_000_000,
    )
    for product in (matching, too_expensive, wrong_brand):
        variant = ProductVariantFactory(
            product=product,
            shop=product.shop,
            original_price=product.min_price,
            sale_price=product.min_price,
        )
        InventoryBalanceFactory(variant=variant, available_stock=5)
    customer = UserFactory(role=User.Role.CUSTOMER)
    session = ChatSession.objects.create(user=customer)
    state = _state(category="Điện thoại", brand="Samsung", price_max=15_000_000)
    assert ProductSelector.public_base().count() == 3
    assert SearchSelector.search({"q": "Samsung"}).count() == 3

    result = AssistantToolRegistry().execute(
        name="search_products",
        arguments={
            "query": "Samsung",
            "category": "Điện thoại",
            "brand": "Samsung",
            "price_max": 15_000_000,
            "in_stock": True,
        },
        context=ToolContext(user=customer, session=session, state=state),
    )

    assert result.ok is True
    assert [item["id"] for item in result.data["products"]] == [str(matching.pk)]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("query", "expected_product_type", "expected_usage", "matching_name", "context_name"),
    (
        (
            "Tìm laptop cho người làm việc từ xa",
            "laptop",
            "làm việc",
            "Laptop Mercato Work 14",
            "Bàn làm việc từ xa cho văn phòng",
        ),
        (
            "Tìm đồng hồ dùng khi chạy bộ",
            "đồng hồ",
            "tập luyện",
            "Đồng hồ chạy bộ Active",
            "Giày chạy bộ cho người mới",
        ),
        (
            "Tìm loa Bluetooth để đi biển",
            "loa Bluetooth",
            "đi biển",
            "Loa Bluetooth chống nước",
            "Kem chống nắng đi biển SPF50",
        ),
    ),
)
def test_product_type_is_hard_scoped_before_context_ranking(
    settings,
    query,
    expected_product_type,
    expected_usage,
    matching_name,
    context_name,
):
    settings.AI_ASSISTANT_RESULT_LIMIT = 4
    category = CategoryFactory(name="Catalog tổng hợp", slug="catalog-tong-hop")
    matching = ProductFactory(
        category=category,
        name=matching_name,
        short_description=f"Phù hợp ngữ cảnh {expected_usage}",
        status=Product.Status.APPROVED,
    )
    context_only = ProductFactory(
        category=category,
        name=context_name,
        short_description=f"Rất phù hợp ngữ cảnh {expected_usage}",
        status=Product.Status.APPROVED,
    )
    for product in (matching, context_only):
        variant = ProductVariantFactory(product=product, shop=product.shop)
        InventoryBalanceFactory(variant=variant, available_stock=5)
    customer = UserFactory(role=User.Role.CUSTOMER)
    session = ChatSession.objects.create(user=customer, turn_count=1)
    understanding = QueryUnderstandingService(ai_service=OfflineAIService()).understand(
        text=query,
        state=ConversationStateRepository.load(session),
        user=customer,
    )
    session, state = ConversationStateRepository.merge_understanding(
        session=session,
        understanding=understanding,
    )
    plan = AssistantPlanner().plan(text=query, understanding=understanding, state=state)

    assert understanding.entities["product_type"].casefold() == expected_product_type.casefold()
    assert understanding.preferences["usage"] == expected_usage
    assert plan.tool_calls[0]["arguments"]["product_type"].casefold() == (
        expected_product_type.casefold()
    )

    result = AssistantToolRegistry().execute(
        name="search_products",
        arguments=plan.tool_calls[0]["arguments"],
        context=ToolContext(user=customer, session=session, state=state),
    )

    assert result.ok is True
    assert [item["id"] for item in result.data["products"]] == [str(matching.pk)]
    assert str(context_only.pk) not in {
        item["id"] for item in result.data["products"]
    }


@pytest.mark.django_db
def test_manual_headphones_for_students_scenario_never_leaks_other_product_types(settings):
    settings.AI_ASSISTANT_RESULT_LIMIT = 4
    category = CategoryFactory(name="Catalog công nghệ", slug="catalog-cong-nghe")
    headphones = ProductFactory(
        category=category,
        name="Tai nghe Samsung Galaxy Buds FE",
        short_description="Tai nghe phù hợp học tập và học trực tuyến.",
        status=Product.Status.APPROVED,
    )
    context_only_products = [
        ProductFactory(
            category=category,
            name=name,
            short_description="Phù hợp học tập, sinh viên và học trực tuyến.",
            status=Product.Status.APPROVED,
        )
        for name in (
            "Laptop MacBook Air",
            "Máy tính bảng iPad Air M2",
            "Điện thoại Samsung Galaxy A55",
        )
    ]
    for product in (headphones, *context_only_products):
        variant = ProductVariantFactory(product=product, shop=product.shop)
        InventoryBalanceFactory(variant=variant, available_stock=5)
    customer = UserFactory(role=User.Role.CUSTOMER)
    session = ChatSession.objects.create(user=customer, turn_count=1)
    text = "Tìm tai nghe cho sinh viên"
    understanding = QueryUnderstandingService(ai_service=OfflineAIService()).understand(
        text=text,
        state=ConversationStateRepository.load(session),
        user=customer,
    )
    session, state = ConversationStateRepository.merge_understanding(
        session=session,
        understanding=understanding,
    )
    plan = AssistantPlanner().plan(text=text, understanding=understanding, state=state)
    result = AssistantToolRegistry().execute(
        name="search_products",
        arguments=plan.tool_calls[0]["arguments"],
        context=ToolContext(user=customer, session=session, state=state),
    )

    assert understanding.entities["product_type"].casefold() == "tai nghe"
    assert understanding.preferences["usage"] == "học tập"
    assert plan.tool_calls[0]["arguments"]["query"].casefold() == "tai nghe"
    assert [item["id"] for item in result.data["products"]] == [str(headphones.pk)]


@pytest.mark.django_db
def test_account_tool_rejects_non_customer_before_query():
    seller = UserFactory(role=User.Role.SELLER)
    session = ChatSession.objects.create(user=seller)

    result = AssistantToolRegistry().execute(
        name="get_order_status",
        arguments={},
        context=ToolContext(user=seller, session=session, state=ConversationState()),
    )

    assert result.ok is False
    assert result.error_code == "authentication_required"


@pytest.mark.django_db
def test_context_expansion_returns_grounded_products_from_multiple_categories(settings):
    settings.AI_ASSISTANT_RESULT_LIMIT = 4
    skincare = CategoryFactory(name="Chăm sóc da", slug="cham-soc-da")
    audio = CategoryFactory(name="Âm thanh", slug="am-thanh")
    sunscreen = ProductFactory(
        category=skincare,
        name="Kem chống nắng đi biển SPF50+",
        description="Chống nắng khi hoạt động ngoài trời.",
        status=Product.Status.APPROVED,
        min_price=450_000,
        max_price=450_000,
    )
    speaker = ProductFactory(
        category=audio,
        name="Loa Bluetooth chống nước",
        description="Loa di động chống nước cho chuyến du lịch.",
        status=Product.Status.APPROVED,
        min_price=2_000_000,
        max_price=2_000_000,
    )
    for product in (sunscreen, speaker):
        variant = ProductVariantFactory(
            product=product,
            shop=product.shop,
            original_price=product.min_price,
            sale_price=product.min_price,
        )
        InventoryBalanceFactory(variant=variant, available_stock=5)
    customer = UserFactory(role=User.Role.CUSTOMER)
    session = ChatSession.objects.create(user=customer)
    state = ConversationState(
        constraints={"query": {"value": "đi biển", "source": "user", "turn": 1}},
        preferences={"usage": {"value": "đi biển", "source": "user", "turn": 1}},
    )

    result = AssistantToolRegistry().execute(
        name="search_products",
        arguments={
            "query": "đi biển",
            "query_terms": ["kem chống nắng", "chống nước", "du lịch"],
            "in_stock": True,
            "limit": 4,
        },
        context=ToolContext(user=customer, session=session, state=state),
    )

    assert result.ok is True
    assert {item["id"] for item in result.data["products"]} == {
        str(sunscreen.pk),
        str(speaker.pk),
    }
    assert {item["kind"] for item in result.data["recommendations"]} == {"personalized"}
    response = GroundedResponseComposer().compose(
        understanding=QueryUnderstanding(
            primary_intent="product_recommendation",
            tasks=("recommend_products",),
        ),
        plan=AssistantPlan(action="search", tasks=("recommend_products",)),
        state=state,
        results=[result],
    )
    assert "ngữ cảnh sử dụng" in response.message
    assert len(response.attachments) == 2


@pytest.mark.django_db
def test_flash_sale_tool_answers_with_live_remaining_time():
    now = timezone.now()
    sale = FlashSale.objects.create(
        name="Flash Sale buổi tối",
        start_time=now - timezone.timedelta(minutes=10),
        end_time=now + timezone.timedelta(hours=1, minutes=30),
    )
    customer = UserFactory(role=User.Role.CUSTOMER)
    session = ChatSession.objects.create(user=customer)

    result = AssistantToolRegistry().execute(
        name="get_flash_sales",
        arguments={"limit": 4},
        context=ToolContext(user=customer, session=session, state=ConversationState()),
    )
    response = GroundedResponseComposer().compose(
        understanding=QueryUnderstanding(
            primary_intent="promotion",
            tasks=("get_flash_sales",),
        ),
        plan=AssistantPlan(action="search", tasks=("get_flash_sales",)),
        state=ConversationState(),
        results=[result],
    )

    assert result.ok is True
    assert result.data["active"][0]["id"] == str(sale.pk)
    assert "Flash Sale buổi tối" in response.message
    assert "còn 1 giờ" in response.message
    assert "chưa tìm thấy sản phẩm" not in response.message

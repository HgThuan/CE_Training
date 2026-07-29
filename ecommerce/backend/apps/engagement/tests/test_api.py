import pytest
from django.urls import reverse

from apps.account.models import User
from apps.account.tests.factories import UserFactory
from apps.engagement.models import ProductAnswer, ProductQuestion
from apps.product.models import Product
from apps.product.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db


def question_url(product) -> str:
    return reverse(
        "engagement:product-question-list",
        kwargs={"product_id": product.pk},
    )


def answer_url(question) -> str:
    return reverse(
        "engagement:product-answer-create",
        kwargs={"question_id": question.pk},
    )


def test_public_questions_are_paginated_visible_and_privacy_safe(
    api_client,
    customer,
    seller,
    product,
):
    visible = ProductQuestion.objects.create(
        product=product,
        customer=customer,
        content="Sản phẩm bảo hành bao lâu?",
    )
    ProductAnswer.objects.create(
        question=visible,
        seller_user=seller,
        content="Bảo hành chính hãng 12 tháng.",
    )
    ProductQuestion.objects.create(
        product=product,
        customer=customer,
        content="Câu hỏi bị ẩn",
        status=ProductQuestion.Status.HIDDEN,
    )

    response = api_client.get(question_url(product), {"page_size": 10})

    assert response.status_code == 200
    assert response.data["meta"]["total_items"] == 1
    assert response.data["data"][0]["id"] == str(visible.pk)
    assert response.data["data"][0]["answer"]["content"] == "Bảo hành chính hãng 12 tháng."
    serialized = str(response.data)
    assert customer.email not in serialized
    assert seller.email not in serialized


def test_customer_can_create_question_and_unknown_fields_are_rejected(
    api_client,
    customer,
    product,
):
    api_client.force_authenticate(customer)

    response = api_client.post(
        question_url(product),
        {"content": "  Có hỗ trợ đổi trả không?  "},
        format="json",
    )
    rejected = api_client.post(
        question_url(product),
        {"content": "Câu hỏi hợp lệ", "status": "hidden"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["data"]["content"] == "Có hỗ trợ đổi trả không?"
    assert response.data["data"]["customer"]["id"] == customer.pk
    assert rejected.status_code == 400
    assert "fields" in rejected.data["errors"]


def test_guest_and_non_customer_cannot_create_question(
    api_client,
    seller,
    product,
):
    guest = api_client.post(
        question_url(product),
        {"content": "Khách chưa đăng nhập"},
        format="json",
    )
    api_client.force_authenticate(seller)
    wrong_role = api_client.post(
        question_url(product),
        {"content": "Seller không được hỏi"},
        format="json",
    )

    assert guest.status_code == 401
    assert wrong_role.status_code == 403
    assert ProductQuestion.objects.count() == 0


def test_only_owner_seller_can_answer_via_api(
    api_client,
    customer,
    seller,
    other_seller,
    product,
):
    question = ProductQuestion.objects.create(
        product=product,
        customer=customer,
        content="Có xuất hóa đơn không?",
    )
    api_client.force_authenticate(other_seller)
    forbidden = api_client.post(
        answer_url(question),
        {"content": "Không được phép trả lời"},
        format="json",
    )
    api_client.force_authenticate(seller)
    created = api_client.post(
        answer_url(question),
        {"content": "Có hỗ trợ xuất hóa đơn."},
        format="json",
    )
    duplicate = api_client.post(
        answer_url(question),
        {"content": "Trả lời lần nữa"},
        format="json",
    )

    assert forbidden.status_code == 403
    assert created.status_code == 201
    assert created.data["data"]["seller"]["id"] == seller.pk
    assert duplicate.status_code == 409


def test_customer_and_guest_cannot_answer(
    api_client,
    customer,
    product,
):
    question = ProductQuestion.objects.create(
        product=product,
        customer=customer,
        content="Có quà tặng không?",
    )
    guest = api_client.post(
        answer_url(question),
        {"content": "Không được"},
        format="json",
    )
    api_client.force_authenticate(customer)
    wrong_role = api_client.post(
        answer_url(question),
        {"content": "Customer không được trả lời"},
        format="json",
    )

    assert guest.status_code == 401
    assert wrong_role.status_code == 403


def test_non_public_product_questions_return_not_found(
    api_client,
    customer,
    shop,
):
    draft = ProductFactory(
        shop=shop,
        status=Product.Status.DRAFT,
    )
    api_client.force_authenticate(customer)

    get_response = api_client.get(question_url(draft))
    post_response = api_client.post(
        question_url(draft),
        {"content": "Không được hỏi sản phẩm nháp"},
        format="json",
    )

    assert get_response.status_code == 404
    assert post_response.status_code == 404


def test_inactive_or_deleted_customer_cannot_create_question(
    api_client,
    product,
):
    inactive = UserFactory(
        role=User.Role.CUSTOMER,
        is_active=False,
    )
    api_client.force_authenticate(inactive)
    inactive_response = api_client.post(
        question_url(product),
        {"content": "Tài khoản bị khóa"},
        format="json",
    )
    deleted = UserFactory(
        role=User.Role.CUSTOMER,
        is_deleted=True,
    )
    api_client.force_authenticate(deleted)
    deleted_response = api_client.post(
        question_url(product),
        {"content": "Tài khoản đã xóa"},
        format="json",
    )

    assert inactive_response.status_code == 403
    assert deleted_response.status_code == 403

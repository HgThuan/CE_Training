import pytest

from apps.common.exceptions import BusinessError
from apps.engagement.models import ProductAnswer, ProductQuestion
from apps.engagement.services import AnswerService, QuestionService

pytestmark = pytest.mark.django_db


def test_customer_creates_trimmed_question(customer, product):
    question = QuestionService.create(
        customer=customer,
        product=product,
        content="  Sản phẩm có chống nước không?  ",
    )

    assert question.content == "Sản phẩm có chống nước không?"
    assert question.status == ProductQuestion.Status.VISIBLE
    assert question.customer == customer
    assert question.product == product


def test_only_customer_can_create_question(seller, product):
    with pytest.raises(BusinessError) as exc_info:
        QuestionService.create(
            customer=seller,
            product=product,
            content="Tôi có thể hỏi không?",
        )

    assert exc_info.value.http_status == 403
    assert ProductQuestion.objects.count() == 0


def test_owner_seller_answers_once(customer, seller, product):
    question = QuestionService.create(
        customer=customer,
        product=product,
        content="Khi nào giao hàng?",
    )

    answer = AnswerService.create(
        seller_user=seller,
        question_id=question.pk,
        content="  Giao trong vòng hai ngày.  ",
    )

    assert answer.content == "Giao trong vòng hai ngày."
    assert answer.seller_user == seller
    assert answer.question == question

    with pytest.raises(BusinessError) as exc_info:
        AnswerService.create(
            seller_user=seller,
            question_id=question.pk,
            content="Câu trả lời thứ hai",
        )

    assert exc_info.value.http_status == 409
    assert ProductAnswer.objects.filter(question=question).count() == 1


def test_seller_cannot_answer_other_shop_question(
    customer,
    other_seller,
    product,
):
    question = QuestionService.create(
        customer=customer,
        product=product,
        content="Sản phẩm còn hàng không?",
    )

    with pytest.raises(BusinessError) as exc_info:
        AnswerService.create(
            seller_user=other_seller,
            question_id=question.pk,
            content="Trả lời trái phép",
        )

    assert exc_info.value.http_status == 403
    assert not ProductAnswer.objects.filter(question=question).exists()


def test_hidden_question_cannot_be_answered(customer, seller, product):
    question = ProductQuestion.objects.create(
        customer=customer,
        product=product,
        content="Câu hỏi đã ẩn",
        status=ProductQuestion.Status.HIDDEN,
    )

    with pytest.raises(BusinessError) as exc_info:
        AnswerService.create(
            seller_user=seller,
            question_id=question.pk,
            content="Không được ghi",
        )

    assert exc_info.value.http_status == 404

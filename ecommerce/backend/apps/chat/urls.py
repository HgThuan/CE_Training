from django.urls import path

from . import views

urlpatterns = [
    path("conversations", views.ConversationListCreateView.as_view()),
    path(
        "conversations/<uuid:conversation_id>/messages",
        views.ConversationMessageListCreateView.as_view(),
    ),
    path("conversations/<uuid:conversation_id>/read", views.ConversationReadView.as_view()),
    path("seller/conversations", views.ConversationListCreateView.as_view()),
    path(
        "seller/conversations/<uuid:conversation_id>/messages",
        views.ConversationMessageListCreateView.as_view(),
    ),
]

from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.InboxView.as_view(), name="inbox"),
    path("new/", views.NewConversationView.as_view(), name="new"),
    path("unread-count/", views.UnreadCountView.as_view(), name="unread_count"),
    path("<uuid:conversation_id>/", views.ConversationView.as_view(), name="conversation"),
    path(
        "<uuid:conversation_id>/messages/",
        views.ConversationMessagesView.as_view(),
        name="conversation_messages",
    ),
]

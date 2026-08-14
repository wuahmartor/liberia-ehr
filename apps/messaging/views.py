from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView, View

from .forms import ComposeMessageForm, MessageForm
from .models import Conversation, Message
from .services import create_message_conversation, send_reply


def is_staff_messenger(user):
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_staff or user.is_superuser:
        return True
    try:
        return user.profile.is_active_staff and user.profile.role != "patient"
    except ObjectDoesNotExist:
        return False


def unread_messages_for(user):
    return Message.objects.filter(conversation__participants=user).exclude(
        sender=user
    ).exclude(read_by=user)


class StaffMessagingAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return is_staff_messenger(self.request.user)

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        return response


class ParticipantConversationMixin(StaffMessagingAccessMixin):
    def get_conversation(self):
        return get_object_or_404(
            Conversation.objects.filter(participants=self.request.user)
            .prefetch_related("participants__profile", "patients")
            .distinct(),
            pk=self.kwargs["conversation_id"],
        )


class InboxView(StaffMessagingAccessMixin, TemplateView):
    template_name = "messaging/inbox.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversations = list(
            Conversation.objects.filter(participants=self.request.user)
            .prefetch_related(
                "participants__profile",
                "patients",
                Prefetch("messages", queryset=Message.objects.select_related("sender")),
                "messages__read_by",
            )
            .distinct()
        )
        for conversation in conversations:
            conversation.chat_partner = conversation.other_participant(self.request.user)
            conversation.is_group_message = conversation.is_broadcast
            cached_messages = list(conversation.messages.all())
            conversation.last_message = cached_messages[-1] if cached_messages else None
            conversation.unread_count = sum(
                1
                for message in cached_messages
                if message.sender_id != self.request.user.pk
                and self.request.user not in message.read_by.all()
            )
        context.update(
            {
                "page_title": "Secure Staff Chat",
                "conversations": conversations,
                "unread_count": unread_messages_for(self.request.user).count(),
                "active_primary_nav": "messaging",
            }
        )
        return context


class NewConversationView(StaffMessagingAccessMixin, FormView):
    template_name = "messaging/new_conversation.html"
    form_class = ComposeMessageForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["current_user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            conversation, _ = create_message_conversation(
                sender=self.request.user,
                subject=form.cleaned_data["subject"],
                body=form.cleaned_data["body"],
                audience=form.cleaned_data["audience"],
                context_type=form.cleaned_data["context_type"],
                subject_category=form.cleaned_data.get("subject_category", ""),
                recipients=form.cleaned_data.get("recipients"),
                patients=form.cleaned_data.get("patients"),
            )
        except ValidationError as exception:
            form.add_error(None, exception.message)
            return self.form_invalid(form)
        return redirect("messaging:conversation", conversation_id=conversation.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"page_title": "New Secure Message", "active_primary_nav": "messaging"})
        return context


class ConversationView(ParticipantConversationMixin, FormView):
    template_name = "messaging/conversation.html"
    form_class = MessageForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not self.test_func():
            return self.handle_no_permission()
        self.conversation = self.get_conversation()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        for message in self.conversation.messages.exclude(sender=request.user).exclude(read_by=request.user):
            message.read_by.add(request.user)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        send_reply(
            conversation=self.conversation,
            sender=self.request.user,
            body=form.cleaned_data["body"],
        )
        return redirect("messaging:conversation", conversation_id=self.conversation.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Secure Conversation",
                "conversation": self.conversation,
                "chat_partner": self.conversation.other_participant(self.request.user),
                "conversation_participants": self.conversation.participants.exclude(
                    pk=self.request.user.pk
                ).select_related("profile"),
                "message_sender": self.conversation.created_by,
                "message_recipients": self.conversation.participants.exclude(
                    pk=self.conversation.created_by_id
                ).select_related("profile"),
                "conversation_messages": self.conversation.messages.select_related(
                    "sender", "sender__profile"
                ).prefetch_related("read_by"),
                "active_primary_nav": "messaging",
            }
        )
        return context


class ConversationMessagesView(ParticipantConversationMixin, TemplateView):
    template_name = "messaging/partials/message_thread.html"

    def get_context_data(self, **kwargs):
        conversation = self.get_conversation()
        for message in conversation.messages.exclude(sender=self.request.user).exclude(
            read_by=self.request.user
        ):
            message.read_by.add(self.request.user)
        return {
            "conversation": conversation,
            "conversation_messages": conversation.messages.select_related(
                "sender", "sender__profile"
            ).prefetch_related("read_by"),
        }


class UnreadCountView(StaffMessagingAccessMixin, View):
    def get(self, request):
        return JsonResponse({"unread_count": unread_messages_for(request.user).count()})

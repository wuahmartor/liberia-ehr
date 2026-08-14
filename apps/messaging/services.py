from django.db import transaction

from django.core.exceptions import ValidationError

from .models import Conversation, Message, PatientCareTeamMember
from .selectors import eligible_staff


def direct_conversation_key(first_user, second_user):
    return ":".join(sorted((str(first_user.pk), str(second_user.pk))))


@transaction.atomic
def send_direct_message(
    *, sender, recipient, body, subject="Secure conversation", context_type="general",
    subject_category=""
):
    key = direct_conversation_key(sender, recipient)
    conversation, created = Conversation.objects.get_or_create(
        direct_key=key,
        defaults={
            "created_by": sender,
            "subject": subject,
            "context_type": context_type,
            "subject_category": subject_category,
        },
    )
    if created:
        conversation.participants.add(sender, recipient)
    elif not conversation.participants.filter(pk=sender.pk).exists():
        raise PermissionError("The sender cannot access this conversation.")

    message = Message(conversation=conversation, sender=sender, body=body.strip())
    message.full_clean(exclude=("read_by",))
    message.save()
    message.read_by.add(sender)
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=message.created_at)
    return conversation, message


def care_team_recipients(patients):
    """Resolve explicit care-team assignments plus recorded encounter providers."""
    from apps.encounters.models import Encounter

    patient_ids = list(patients.values_list("pk", flat=True))
    explicit_ids = PatientCareTeamMember.objects.filter(
        patient_id__in=patient_ids,
        is_active=True,
        user__is_active=True,
    ).values_list("user_id", flat=True)
    provider_ids = Encounter.objects.filter(
        patient_id__in=patient_ids,
        attending_provider__isnull=False,
        attending_provider__is_active=True,
    ).values_list("attending_provider_id", flat=True)
    return eligible_staff().filter(pk__in=set(explicit_ids) | set(provider_ids))


@transaction.atomic
def create_message_conversation(
    *, sender, subject, body, audience, recipients=None, patients=None,
    context_type=Conversation.ContextType.GENERAL, subject_category=""
):
    patients = patients or []
    if audience == Conversation.Audience.ALL_STAFF:
        resolved_recipients = eligible_staff().exclude(pk=sender.pk)
    elif audience == Conversation.Audience.CARE_TEAM:
        resolved_recipients = care_team_recipients(patients).exclude(pk=sender.pk)
    else:
        resolved_recipients = eligible_staff().filter(
            pk__in=[user.pk for user in (recipients or [])]
        ).exclude(pk=sender.pk)

    recipient_ids = list(resolved_recipients.values_list("pk", flat=True))
    if not recipient_ids:
        raise ValidationError("The selected audience has no eligible recipients.")

    conversation = Conversation.objects.create(
        created_by=sender,
        subject=subject.strip(),
        audience=audience,
        context_type=context_type,
        subject_category=subject_category,
    )
    conversation.participants.add(sender, *recipient_ids)
    if patients:
        conversation.patients.add(*patients)

    message = Message(conversation=conversation, sender=sender, body=body.strip())
    message.full_clean(exclude=("read_by",))
    message.save()
    message.read_by.add(sender)
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=message.created_at)
    return conversation, message


@transaction.atomic
def send_reply(*, conversation, sender, body):
    if not conversation.participants.filter(pk=sender.pk).exists():
        raise PermissionError("The sender cannot access this conversation.")
    message = Message(conversation=conversation, sender=sender, body=body.strip())
    message.full_clean(exclude=("read_by",))
    message.save()
    message.read_by.add(sender)
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=message.created_at)
    return message

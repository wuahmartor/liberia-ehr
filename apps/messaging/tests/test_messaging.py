from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import UserProfile
from apps.patients.models import Patient

from ..models import Conversation, Message, PatientCareTeamMember
from ..services import create_message_conversation, send_direct_message

User = get_user_model()


class SecureMessagingTests(TestCase):
    def make_staff(self, username):
        user = User.objects.create_user(username=username, password="test-password")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.is_active_staff = True
        profile.save(update_fields=("is_active_staff", "updated_at"))
        return user

    def setUp(self):
        self.sender = self.make_staff("sender")
        self.recipient = self.make_staff("recipient")
        self.outsider = self.make_staff("outsider")
        self.conversation, self.message = send_direct_message(
            sender=self.sender,
            recipient=self.recipient,
            body="Confidential handoff",
        )

    def test_only_participants_can_open_conversation(self):
        self.client.force_login(self.outsider)
        response = self.client.get(
            reverse("messaging:conversation", args=(self.conversation.pk,))
        )
        self.assertEqual(response.status_code, 404)

    def test_recipient_unread_count_clears_when_thread_is_opened(self):
        self.client.force_login(self.recipient)
        count_response = self.client.get(reverse("messaging:unread_count"))
        self.assertEqual(count_response.json()["unread_count"], 1)

        self.client.get(reverse("messaging:conversation", args=(self.conversation.pk,)))

        count_response = self.client.get(reverse("messaging:unread_count"))
        self.assertEqual(count_response.json()["unread_count"], 0)
        self.assertTrue(self.message.read_by.filter(pk=self.recipient.pk).exists())

    def test_sender_is_automatically_marked_as_having_read_message(self):
        self.assertTrue(self.message.read_by.filter(pk=self.sender.pk).exists())

    def test_authenticated_staff_sees_chat_entry_in_green_user_bar(self):
        self.client.force_login(self.sender)

        response = self.client.get(reverse("messaging:inbox"))

        self.assertContains(response, "Secure Staff Messaging")
        self.assertContains(response, ">Messages</span>", html=False)
        self.assertContains(response, reverse("messaging:unread_count"))

    def test_compose_screen_has_searchable_recipient_and_patient_adders(self):
        patient = self.make_patient()
        self.client.force_login(self.sender)

        response = self.client.get(reverse("messaging:new"))

        self.assertContains(response, "Search staff by name or title")
        self.assertContains(response, "Search patients by name or MRN")
        self.assertContains(response, self.recipient.username)
        self.assertContains(response, patient.mrn)
        self.assertContains(response, "Concerned patients")
        self.assertContains(response, "Change of condition")
        self.assertLess(
            response.content.index(b"Message context"),
            response.content.index(b"Patient subject category"),
        )

    def test_non_staff_user_is_forbidden(self):
        user = User.objects.create_user(username="nonstaff", password="test-password")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.is_active_staff = False
        profile.save(update_fields=("is_active_staff", "updated_at"))
        self.client.force_login(user)

        response = self.client.get(reverse("messaging:inbox"))

        self.assertEqual(response.status_code, 403)

    def test_patient_profile_is_forbidden(self):
        user = User.objects.create_user(username="patient-user", password="test-password")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.Role.PATIENT
        profile.is_active_staff = True
        profile.save(update_fields=("role", "is_active_staff", "updated_at"))
        self.client.force_login(user)

        response = self.client.get(reverse("messaging:inbox"))

        self.assertEqual(response.status_code, 403)

    def test_staff_can_start_conversation_and_send_message(self):
        new_recipient = self.make_staff("new-recipient")
        self.client.force_login(self.sender)

        response = self.client.post(
            reverse("messaging:new"),
            {
                "subject": "Handoff review",
                "context_type": "general",
                "audience": "specific",
                "recipients": [new_recipient.pk],
                "body": "Please review this handoff.",
            },
        )

        conversation = Conversation.objects.get(participants=new_recipient)
        self.assertRedirects(
            response,
            reverse("messaging:conversation", args=(conversation.pk,)),
        )
        self.assertTrue(
            conversation.messages.filter(
                sender=self.sender, body="Please review this handoff."
            ).exists()
        )

    def make_patient(self, mrn="MRN-CHAT-1"):
        return Patient.objects.create(
            mrn=mrn,
            first_name="Test",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            created_by=self.sender,
            updated_by=self.sender,
        )

    def test_message_can_link_multiple_patients(self):
        first_patient = self.make_patient()
        second_patient = self.make_patient("MRN-CHAT-2")

        conversation, _ = create_message_conversation(
            sender=self.sender,
            subject="Shared care coordination",
            body="Coordinate both patient visits.",
            audience=Conversation.Audience.SPECIFIC,
            recipients=[self.recipient],
            patients=Patient.objects.filter(pk__in=(first_patient.pk, second_patient.pk)),
        )

        self.assertEqual(conversation.patients.count(), 2)
        self.assertEqual(conversation.subject, "Shared care coordination")

    def test_patient_context_builds_subject_from_category_and_details(self):
        patient = self.make_patient()
        self.client.force_login(self.sender)

        response = self.client.post(
            reverse("messaging:new"),
            {
                "context_type": Conversation.ContextType.PATIENT,
                "subject_category": Conversation.SubjectCategory.CHANGE_OF_CONDITION,
                "subject": "Increasing oxygen requirement",
                "patients": [patient.pk],
                "audience": Conversation.Audience.SPECIFIC,
                "recipients": [self.recipient.pk],
                "body": "Please review the patient now.",
            },
        )

        conversation = Conversation.objects.get(subject__contains="Increasing oxygen")
        self.assertRedirects(
            response,
            reverse("messaging:conversation", args=(conversation.pk,)),
        )
        self.assertEqual(conversation.context_type, Conversation.ContextType.PATIENT)
        self.assertEqual(
            conversation.subject_category,
            Conversation.SubjectCategory.CHANGE_OF_CONDITION,
        )
        self.assertEqual(
            conversation.subject,
            "Change of condition — Increasing oxygen requirement",
        )

    def test_thread_distinguishes_received_and_sent_messages(self):
        self.client.force_login(self.recipient)

        received_response = self.client.get(
            reverse("messaging:conversation_messages", args=(self.conversation.pk,))
        )

        self.assertContains(received_response, 'data-message-direction="received"')
        self.assertContains(received_response, "Confidential handoff")
        self.assertNotContains(received_response, "Received from")

        self.client.post(
            reverse("messaging:conversation", args=(self.conversation.pk,)),
            {"body": "Acknowledged."},
        )
        sent_response = self.client.get(
            reverse("messaging:conversation_messages", args=(self.conversation.pk,))
        )
        self.assertContains(sent_response, 'data-message-direction="sent"')
        self.assertContains(sent_response, "Sent by you")

    def test_conversation_displays_context_patients_and_all_recipients(self):
        patient = self.make_patient()
        conversation, _ = create_message_conversation(
            sender=self.sender,
            subject="Diagnostic results",
            body="Results are available.",
            audience=Conversation.Audience.SPECIFIC,
            recipients=[self.recipient, self.outsider],
            patients=Patient.objects.filter(pk=patient.pk),
            context_type=Conversation.ContextType.PATIENT,
            subject_category=Conversation.SubjectCategory.DIAGNOSTIC_RESULTS,
        )
        self.client.force_login(self.recipient)

        response = self.client.get(
            reverse("messaging:conversation", args=(conversation.pk,))
        )

        self.assertContains(response, "Diagnostic results")
        self.assertContains(response, patient.mrn)
        self.assertContains(response, self.sender.username)
        self.assertContains(response, self.recipient.username)
        self.assertContains(response, self.outsider.username)
        self.assertNotContains(response, "All recipients (2)")

    def test_care_team_broadcast_uses_explicit_patient_assignments(self):
        patient = self.make_patient()
        PatientCareTeamMember.objects.create(
            patient=patient,
            user=self.recipient,
            assigned_by=self.sender,
            role_label="Primary nurse",
        )

        conversation, _ = create_message_conversation(
            sender=self.sender,
            subject="Care team update",
            body="New care plan is available.",
            audience=Conversation.Audience.CARE_TEAM,
            patients=Patient.objects.filter(pk=patient.pk),
        )

        self.assertTrue(conversation.participants.filter(pk=self.recipient.pk).exists())
        self.assertFalse(conversation.participants.filter(pk=self.outsider.pk).exists())

    def test_all_staff_broadcast_reaches_every_eligible_staff_user(self):
        conversation, _ = create_message_conversation(
            sender=self.sender,
            subject="System-wide update",
            body="Please review the new workflow.",
            audience=Conversation.Audience.ALL_STAFF,
        )

        self.assertTrue(conversation.participants.filter(pk=self.recipient.pk).exists())
        self.assertTrue(conversation.participants.filter(pk=self.outsider.pk).exists())

    def test_message_body_is_escaped_in_conversation(self):
        Message.objects.create(
            conversation=self.conversation,
            sender=self.sender,
            body="<script>alert('xss')</script>",
        )
        self.client.force_login(self.recipient)

        response = self.client.get(
            reverse("messaging:conversation", args=(self.conversation.pk,))
        )

        self.assertNotContains(response, "<script>", html=False)
        self.assertContains(response, "&lt;script&gt;", html=False)

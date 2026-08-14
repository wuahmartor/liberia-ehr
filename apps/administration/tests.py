from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from .forms import RoleGroupForm


class GroupPermissionAdministrationTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username="administrator",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    def test_group_list_is_available_in_access_and_security(self):
        Group.objects.create(name="Nurses")

        response = self.client.get(reverse("administration:roles"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Groups and Permissions")
        self.assertContains(response, "Nurses")
        self.assertContains(response, "Add group")

    def test_staff_user_can_create_group_with_permissions(self):
        permission = Permission.objects.select_related("content_type").first()

        response = self.client.post(
            reverse("administration:role_create"),
            {"name": "Billing", "permissions": [permission.pk]},
        )

        self.assertRedirects(response, reverse("administration:roles"))
        group = Group.objects.get(name="Billing")
        self.assertQuerySetEqual(group.permissions.all(), [permission])

    def test_permission_choices_are_grouped_by_application(self):
        permission = Permission.objects.select_related("content_type").first()
        group = Group.objects.create(name="Clinicians")
        group.permissions.add(permission)

        sections = dict(RoleGroupForm(instance=group).permission_groups())

        self.assertIn(permission.content_type.app_label, sections)
        selected = [
            item
            for item in sections[permission.content_type.app_label]
            if item["permission"] == permission
        ]
        self.assertTrue(selected[0]["selected"])

    def test_non_staff_user_cannot_manage_groups(self):
        user = get_user_model().objects.create_user(
            username="standard-user", password="test-password"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("administration:roles"))

        self.assertEqual(response.status_code, 403)

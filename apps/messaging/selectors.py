from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


def eligible_staff():
    """Active non-patient users authorized to access staff records."""
    return (
        User.objects.select_related("profile")
        .filter(is_active=True)
        .filter(Q(is_staff=True) | Q(is_superuser=True) | Q(profile__is_active_staff=True))
        .exclude(profile__role="patient")
        .distinct()
    )

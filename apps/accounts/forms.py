

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


class EHRLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": (
                    "block w-full rounded-lg border border-slate-300 "
                    "bg-white px-4 py-3 text-slate-900 shadow-sm "
                    "outline-none transition focus:border-blue-600 "
                    "focus:ring-2 focus:ring-blue-200"
                ),
                "placeholder": "Enter your username",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": (
                    "block w-full rounded-lg border border-slate-300 "
                    "bg-white px-4 py-3 text-slate-900 shadow-sm "
                    "outline-none transition focus:border-blue-600 "
                    "focus:ring-2 focus:ring-blue-200"
                ),
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )

    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        label="Keep me signed in",
        widget=forms.CheckboxInput(
            attrs={
                "class": (
                    "h-4 w-4 rounded border-slate-300 "
                    "text-blue-700 focus:ring-blue-600"
                ),
            }
        ),
    )

    error_messages = {
        "invalid_login": (
            "The username or password is incorrect. "
            "Please verify your credentials and try again."
        ),
        "inactive": (
            "This account is inactive. Contact your system administrator."
        ),
    }

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password,
            )

            if self.user_cache is None:
                raise self.get_invalid_login_error()

            self.confirm_login_allowed(self.user_cache)

            profile = getattr(self.user_cache, "profile", None)

            if profile and not profile.is_active_staff:
                raise ValidationError(
                    "Your staff profile has been deactivated. "
                    "Contact your facility administrator.",
                    code="inactive_profile",
                )

        return self.cleaned_data
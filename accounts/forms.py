from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User, normalize_phone_number


class SignUpForm(forms.Form):
    phone_number = forms.CharField(
        label="Phone Number",
        widget=forms.TextInput(attrs={"placeholder": "07XXXXXXXX", "autocomplete": "tel"}),
    )
    full_name = forms.CharField(label="Full Name", required=False, max_length=120)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)
    referral_code = forms.CharField(
        label="Referral Code (optional)", required=False, max_length=12
    )

    def clean_phone_number(self):
        raw = self.cleaned_data["phone_number"]
        try:
            normalized = normalize_phone_number(raw)
        except ValidationError as exc:
            raise forms.ValidationError(exc.message)
        if User.objects.filter(phone_number=normalized).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return normalized

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        validate_password(password1)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class PhoneAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Phone Number",
        widget=forms.TextInput(attrs={"placeholder": "07XXXXXXXX", "autocomplete": "tel", "autofocus": True}),
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name"]
        widgets = {"full_name": forms.TextInput(attrs={"placeholder": "Your full name"})}


class AdminUserCreationForm(DjangoUserCreationForm):
    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("phone_number", "full_name")


class AdminUserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = "__all__"

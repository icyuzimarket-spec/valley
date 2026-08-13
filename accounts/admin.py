from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import AdminUserChangeForm, AdminUserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    ordering = ["-date_joined"]
    list_display = [
        "phone_number",
        "full_name",
        "balance",
        "referred_by",
        "is_fallback_referral",
        "is_staff",
        "is_active",
        "date_joined",
    ]
    search_fields = ["phone_number", "full_name", "referral_code"]
    list_filter = ["is_staff", "is_active", "is_fallback_referral"]
    readonly_fields = ["referral_code", "date_joined", "last_withdrawal_request_at"]

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal info", {"fields": ("full_name",)}),
        (
            "Referral",
            {"fields": ("referral_code", "referred_by", "is_fallback_referral")},
        ),
        (
            "Wallet",
            {"fields": ("balance", "welcome_bonus_paid", "last_withdrawal_request_at")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_number", "full_name", "password1", "password2"),
            },
        ),
    )

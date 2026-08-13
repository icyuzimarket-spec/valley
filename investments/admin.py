from django.contrib import admin
from django.utils.html import format_html

from . import services
from .models import Investment, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["level", "price", "daily_income", "all_return", "duration_days", "is_active"]
    ordering = ["level"]


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "plan",
        "amount",
        "status",
        "screenshot_thumb",
        "days_credited",
        "is_completed",
        "created_at",
    ]
    list_filter = ["status", "plan", "is_completed"]
    search_fields = ["user__phone_number", "user__full_name"]
    readonly_fields = [
        "user",
        "plan",
        "amount",
        "daily_income",
        "duration_days",
        "screenshot_preview",
        "created_at",
        "reviewed_at",
        "reviewed_by",
        "start_date",
        "last_credited_date",
        "days_credited",
        "is_completed",
    ]
    fields = [
        "user",
        "plan",
        "amount",
        "daily_income",
        "duration_days",
        "status",
        "rejection_reason",
        "screenshot_preview",
        "created_at",
        "reviewed_at",
        "reviewed_by",
        "start_date",
        "last_credited_date",
        "days_credited",
        "is_completed",
    ]
    actions = ["approve_selected", "reject_selected"]

    def screenshot_thumb(self, obj):
        if obj.payment_screenshot:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:4px;" />', obj.payment_screenshot.url
            )
        return "-"

    screenshot_thumb.short_description = "Proof"

    def screenshot_preview(self, obj):
        if obj.payment_screenshot:
            return format_html(
                '<img src="{}" style="max-height:400px;border-radius:8px;" />', obj.payment_screenshot.url
            )
        return "-"

    screenshot_preview.short_description = "Payment Screenshot"

    def has_change_permission(self, request, obj=None):
        # Status changes must go through approve/reject actions so bonuses
        # and commissions can never be bypassed by hand-editing the field.
        return False

    @admin.action(description="Approve selected pending investments")
    def approve_selected(self, request, queryset):
        count = 0
        for inv in queryset.filter(status=Investment.STATUS_PENDING):
            services.approve_investment(inv, request.user)
            count += 1
        self.message_user(request, f"Approved {count} investment(s).")

    @admin.action(description="Reject selected pending investments")
    def reject_selected(self, request, queryset):
        count = 0
        for inv in queryset.filter(status=Investment.STATUS_PENDING):
            services.reject_investment(inv, request.user, reason="Rejected via admin")
            count += 1
        self.message_user(request, f"Rejected {count} investment(s).")

from django.contrib import admin

from . import services
from .models import Transaction, Withdrawal


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "type", "amount", "balance_after", "created_at"]
    list_filter = ["type"]
    search_fields = ["user__phone_number", "user__full_name"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "amount", "status", "requested_at", "reviewed_at"]
    list_filter = ["status"]
    search_fields = ["user__phone_number", "user__full_name"]
    readonly_fields = ["user", "amount", "requested_at", "reviewed_at", "reviewed_by"]
    actions = ["approve_selected", "reject_selected"]

    def has_change_permission(self, request, obj=None):
        return False

    @admin.action(description="Approve selected withdrawals")
    def approve_selected(self, request, queryset):
        count = 0
        for w in queryset.filter(status=Withdrawal.STATUS_PENDING):
            services.approve_withdrawal(w, request.user)
            count += 1
        self.message_user(request, f"Approved {count} withdrawal(s).")

    @admin.action(description="Reject selected withdrawals (refunds balance)")
    def reject_selected(self, request, queryset):
        count = 0
        for w in queryset.filter(status=Withdrawal.STATUS_PENDING):
            services.reject_withdrawal(w, request.user, reason="Rejected via admin")
            count += 1
        self.message_user(request, f"Rejected {count} withdrawal(s).")

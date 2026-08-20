from django.contrib import admin

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fields = [
        "whatsapp_number",
        "whatsapp_group_url",
        "telegram_group_url",
        "payee_name",
        "payment_code",
        "fallback_referrer",
        "min_withdrawal",
        "maintenance_notice",
        "maintenance_message",
    ]

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

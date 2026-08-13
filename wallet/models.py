from django.conf import settings
from django.db import models


class Transaction(models.Model):
    TYPE_DAILY_INCOME = "daily_income"
    TYPE_WELCOME_BONUS = "welcome_bonus"
    TYPE_REFERRAL_COMMISSION = "referral_commission"
    TYPE_WITHDRAWAL = "withdrawal"
    TYPE_WITHDRAWAL_REVERSAL = "withdrawal_reversal"
    TYPE_CHOICES = [
        (TYPE_DAILY_INCOME, "Daily Income"),
        (TYPE_WELCOME_BONUS, "Welcome Bonus"),
        (TYPE_REFERRAL_COMMISSION, "Referral Commission"),
        (TYPE_WITHDRAWAL, "Withdrawal"),
        (TYPE_WITHDRAWAL_REVERSAL, "Withdrawal Reversal"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )
    type = models.CharField(max_length=25, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    investment = models.ForeignKey(
        "investments.Investment", null=True, blank=True, on_delete=models.SET_NULL
    )
    withdrawal = models.ForeignKey(
        "wallet.Withdrawal", null=True, blank=True, on_delete=models.SET_NULL
    )
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.get_type_display()} - {self.amount}"


class Withdrawal(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdrawals"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_withdrawals",
    )
    admin_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.user} - {self.amount} - {self.status}"

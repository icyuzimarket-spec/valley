from django.conf import settings
from django.db import models


class Plan(models.Model):
    level = models.PositiveSmallIntegerField(unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    daily_income = models.DecimalField(max_digits=12, decimal_places=2)
    all_return = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.PositiveSmallIntegerField(default=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["level"]

    def __str__(self):
        return f"Valley Lev {self.level}"


class Investment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="investments"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="investments")

    # Snapshot of plan terms at the time of investment, so later Plan edits
    # never retroactively change an already-running investment.
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    daily_income = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.PositiveSmallIntegerField()

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_screenshot = models.ImageField(upload_to="payment_proofs/%Y/%m/")

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_investments",
    )
    rejection_reason = models.CharField(max_length=255, blank=True)

    start_date = models.DateField(null=True, blank=True)
    last_credited_date = models.DateField(null=True, blank=True)
    days_credited = models.PositiveSmallIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.plan} - {self.status}"

    @property
    def total_return(self):
        return self.daily_income * self.duration_days

    @property
    def progress_percent(self):
        if not self.duration_days:
            return 0
        return round(min(self.days_credited, self.duration_days) / self.duration_days * 100)

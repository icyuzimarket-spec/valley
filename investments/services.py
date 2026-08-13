from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Investment


def credit_due_earnings(investment: Investment) -> None:
    """Self-healing daily accrual: credits any days owed since the last credit,
    capped at the investment's duration. Safe to call any number of times."""
    if investment.status != Investment.STATUS_APPROVED:
        return
    if investment.is_completed or investment.start_date is None:
        return

    from wallet.models import Transaction

    with transaction.atomic():
        inv = Investment.objects.select_for_update().get(pk=investment.pk)
        if inv.status != Investment.STATUS_APPROVED or inv.is_completed or inv.start_date is None:
            return

        today = timezone.localdate()
        elapsed = min((today - inv.start_date).days + 1, inv.duration_days)
        days_to_credit = elapsed - inv.days_credited
        if days_to_credit <= 0:
            return

        User = inv.user.__class__
        user = User.objects.select_for_update().get(pk=inv.user_id)
        amount = inv.daily_income * days_to_credit
        user.balance += amount
        user.save(update_fields=["balance"])

        Transaction.objects.create(
            user=user,
            type=Transaction.TYPE_DAILY_INCOME,
            amount=amount,
            balance_after=user.balance,
            investment=inv,
            note=f"{days_to_credit} day(s) of income for {inv.plan}",
        )

        inv.days_credited = elapsed
        inv.last_credited_date = today
        inv.is_completed = elapsed >= inv.duration_days
        inv.save(update_fields=["days_credited", "last_credited_date", "is_completed"])


def sync_active_investments(user) -> None:
    investments = Investment.objects.filter(
        user=user, status=Investment.STATUS_APPROVED, is_completed=False
    )
    for inv in investments:
        credit_due_earnings(inv)


def approve_investment(investment: Investment, admin_user) -> Investment:
    from wallet.models import Transaction

    with transaction.atomic():
        inv = Investment.objects.select_for_update().get(pk=investment.pk)
        if inv.status != Investment.STATUS_PENDING:
            return inv  # already handled - idempotent against double-click/double-approve

        User = inv.user.__class__
        user = User.objects.select_for_update().get(pk=inv.user_id)

        is_first_approval = not Investment.objects.filter(
            user=user, status=Investment.STATUS_APPROVED
        ).exclude(pk=inv.pk).exists()

        inv.status = Investment.STATUS_APPROVED
        inv.reviewed_at = timezone.now()
        inv.reviewed_by = admin_user
        inv.start_date = timezone.localdate()
        inv.save()

        update_fields = []
        if is_first_approval and not user.welcome_bonus_paid:
            user.balance += settings.WELCOME_BONUS_AMOUNT
            user.welcome_bonus_paid = True
            update_fields += ["balance", "welcome_bonus_paid"]
            Transaction.objects.create(
                user=user,
                type=Transaction.TYPE_WELCOME_BONUS,
                amount=settings.WELCOME_BONUS_AMOUNT,
                balance_after=user.balance,
                investment=inv,
                note="One-time welcome bonus",
            )

        if is_first_approval and user.referred_by_id and not user.is_fallback_referral:
            referrer = User.objects.select_for_update().get(pk=user.referred_by_id)
            commission = (inv.amount * settings.REFERRAL_COMMISSION_RATE).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            referrer.balance += commission
            referrer.save(update_fields=["balance"])
            Transaction.objects.create(
                user=referrer,
                type=Transaction.TYPE_REFERRAL_COMMISSION,
                amount=commission,
                balance_after=referrer.balance,
                investment=inv,
                note=f"8% commission from {user}'s first investment",
            )

        if update_fields:
            user.save(update_fields=list(set(update_fields)))

        credit_due_earnings(inv)

    return inv


def reject_investment(investment: Investment, admin_user, reason: str = "") -> Investment:
    with transaction.atomic():
        inv = Investment.objects.select_for_update().get(pk=investment.pk)
        if inv.status != Investment.STATUS_PENDING:
            return inv
        inv.status = Investment.STATUS_REJECTED
        inv.reviewed_at = timezone.now()
        inv.reviewed_by = admin_user
        inv.rejection_reason = reason
        inv.save()
    return inv

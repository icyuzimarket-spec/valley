from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Transaction, Withdrawal

WITHDRAWAL_OPEN_TIME = time.fromisoformat(settings.WITHDRAWAL_OPEN_TIME)
WITHDRAWAL_CLOSE_TIME = time.fromisoformat(settings.WITHDRAWAL_CLOSE_TIME)
SUNDAY = 6


class WithdrawalNotAllowed(Exception):
    def __init__(self, next_eligible: datetime):
        self.next_eligible = next_eligible
        super().__init__(f"Withdrawals are not open until {next_eligible}.")


class InsufficientBalance(Exception):
    pass


def next_withdrawal_window(user) -> datetime:
    """Returns the next datetime at which `user` may submit a withdrawal
    request, honoring the 24h cooldown, Mon-Sat 06:30-23:30 window, and no
    withdrawals on Sunday. Rolls forward past closed periods."""
    now = timezone.localtime()
    if user.last_withdrawal_request_at:
        earliest = timezone.localtime(user.last_withdrawal_request_at) + timedelta(
            hours=settings.WITHDRAWAL_COOLDOWN_HOURS
        )
        candidate = max(now, earliest)
    else:
        candidate = now

    for _ in range(30):  # bounded guard against unforeseen infinite loops
        if candidate.weekday() == SUNDAY:
            candidate = (candidate + timedelta(days=1)).replace(
                hour=WITHDRAWAL_OPEN_TIME.hour,
                minute=WITHDRAWAL_OPEN_TIME.minute,
                second=0,
                microsecond=0,
            )
            continue
        if candidate.time() < WITHDRAWAL_OPEN_TIME:
            candidate = candidate.replace(
                hour=WITHDRAWAL_OPEN_TIME.hour,
                minute=WITHDRAWAL_OPEN_TIME.minute,
                second=0,
                microsecond=0,
            )
            continue
        if candidate.time() > WITHDRAWAL_CLOSE_TIME:
            candidate = (candidate + timedelta(days=1)).replace(
                hour=WITHDRAWAL_OPEN_TIME.hour,
                minute=WITHDRAWAL_OPEN_TIME.minute,
                second=0,
                microsecond=0,
            )
            continue
        return candidate

    raise RuntimeError("Could not resolve next withdrawal window.")


def request_withdrawal(user, amount) -> Withdrawal:
    with transaction.atomic():
        User = user.__class__
        user = User.objects.select_for_update().get(pk=user.pk)
        now = timezone.now()

        window = next_withdrawal_window(user)
        if now < window:
            raise WithdrawalNotAllowed(window)

        site_settings = _site_settings()
        if amount <= 0 or amount > user.balance or (
            site_settings.min_withdrawal and amount < site_settings.min_withdrawal
        ):
            raise InsufficientBalance()

        user.balance -= amount
        user.last_withdrawal_request_at = now
        user.save(update_fields=["balance", "last_withdrawal_request_at"])

        withdrawal = Withdrawal.objects.create(
            user=user, amount=amount, status=Withdrawal.STATUS_PENDING, requested_at=now
        )
        Transaction.objects.create(
            user=user,
            type=Transaction.TYPE_WITHDRAWAL,
            amount=-amount,
            balance_after=user.balance,
            withdrawal=withdrawal,
            note="Withdrawal requested",
        )
    return withdrawal


def approve_withdrawal(withdrawal: Withdrawal, admin_user) -> Withdrawal:
    with transaction.atomic():
        w = Withdrawal.objects.select_for_update().get(pk=withdrawal.pk)
        if w.status != Withdrawal.STATUS_PENDING:
            return w
        w.status = Withdrawal.STATUS_APPROVED
        w.reviewed_at = timezone.now()
        w.reviewed_by = admin_user
        w.save()
    return w


def reject_withdrawal(withdrawal: Withdrawal, admin_user, reason: str = "") -> Withdrawal:
    with transaction.atomic():
        w = Withdrawal.objects.select_for_update().get(pk=withdrawal.pk)
        if w.status != Withdrawal.STATUS_PENDING:
            return w

        User = w.user.__class__
        user = User.objects.select_for_update().get(pk=w.user_id)
        user.balance += w.amount
        user.save(update_fields=["balance"])

        w.status = Withdrawal.STATUS_REJECTED
        w.reviewed_at = timezone.now()
        w.reviewed_by = admin_user
        w.admin_note = reason
        w.save()

        Transaction.objects.create(
            user=user,
            type=Transaction.TYPE_WITHDRAWAL_REVERSAL,
            amount=w.amount,
            balance_after=user.balance,
            withdrawal=w,
            note="Withdrawal rejected - refunded",
        )
    return w


def _site_settings():
    from core.models import SiteSettings

    return SiteSettings.load()

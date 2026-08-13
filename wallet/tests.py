from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from accounts.models import User

from . import services
from .models import Withdrawal


def aware(year, month, day, hour, minute):
    return timezone.make_aware(datetime(year, month, day, hour, minute))


class NextWithdrawalWindowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("0788111111", "strongpass123")

    @patch("django.utils.timezone.now")
    def test_no_prior_request_inside_window_returns_now(self, mock_now):
        # 2026-08-10 is a Monday, well inside 06:30-23:30.
        now = aware(2026, 8, 10, 12, 0)
        mock_now.return_value = now
        window = services.next_withdrawal_window(self.user)
        self.assertEqual(window, now)

    @patch("django.utils.timezone.now")
    def test_before_opening_time_rolls_to_opening(self, mock_now):
        mock_now.return_value = aware(2026, 8, 10, 5, 0)  # Monday 05:00
        window = services.next_withdrawal_window(self.user)
        self.assertEqual((window.hour, window.minute), (6, 30))
        self.assertEqual(window.date(), aware(2026, 8, 10, 0, 0).date())

    @patch("django.utils.timezone.now")
    def test_after_closing_time_rolls_to_next_day_opening(self, mock_now):
        mock_now.return_value = aware(2026, 8, 10, 23, 45)  # Monday 23:45
        window = services.next_withdrawal_window(self.user)
        self.assertEqual((window.hour, window.minute), (6, 30))
        self.assertEqual(window.date(), aware(2026, 8, 11, 0, 0).date())

    @patch("django.utils.timezone.now")
    def test_skips_sunday_entirely(self, mock_now):
        mock_now.return_value = aware(2026, 8, 9, 10, 0)  # Sunday
        window = services.next_withdrawal_window(self.user)
        self.assertEqual(window.weekday(), 0)  # rolled to Monday
        self.assertEqual((window.hour, window.minute), (6, 30))

    @patch("django.utils.timezone.now")
    def test_24h_cooldown_enforced(self, mock_now):
        now = aware(2026, 8, 10, 12, 0)
        mock_now.return_value = now
        self.user.last_withdrawal_request_at = now
        self.user.save()
        window = services.next_withdrawal_window(self.user)
        self.assertEqual(window, now + timedelta(hours=24))

    @patch("django.utils.timezone.now")
    def test_cooldown_expiring_on_sunday_rolls_to_monday(self, mock_now):
        # Last request Saturday noon -> cooldown expires Sunday noon -> must roll to Monday 06:30.
        saturday_noon = aware(2026, 8, 8, 12, 0)
        self.assertEqual(saturday_noon.weekday(), 5)
        self.user.last_withdrawal_request_at = saturday_noon
        self.user.save()
        mock_now.return_value = saturday_noon
        window = services.next_withdrawal_window(self.user)
        self.assertEqual(window.weekday(), 0)
        self.assertEqual((window.hour, window.minute), (6, 30))


class RequestWithdrawalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("0788222222", "strongpass123")
        self.user.balance = Decimal("5000.00")
        self.user.save()

    @patch("django.utils.timezone.now")
    def test_request_debits_balance_and_creates_pending_withdrawal(self, mock_now):
        mock_now.return_value = aware(2026, 8, 10, 12, 0)  # Monday noon - open
        w = services.request_withdrawal(self.user, Decimal("1000.00"))

        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("4000.00"))
        self.assertEqual(w.status, Withdrawal.STATUS_PENDING)
        self.assertIsNotNone(self.user.last_withdrawal_request_at)

    @patch("django.utils.timezone.now")
    def test_rejects_amount_over_balance(self, mock_now):
        mock_now.return_value = aware(2026, 8, 10, 12, 0)
        with self.assertRaises(services.InsufficientBalance):
            services.request_withdrawal(self.user, Decimal("999999.00"))

    @patch("django.utils.timezone.now")
    def test_blocked_outside_window(self, mock_now):
        mock_now.return_value = aware(2026, 8, 9, 12, 0)  # Sunday
        with self.assertRaises(services.WithdrawalNotAllowed):
            services.request_withdrawal(self.user, Decimal("1000.00"))


class ApproveRejectWithdrawalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("0788333333", "strongpass123")
        self.admin = User.objects.create_superuser("0700000000", "adminpass123")
        self.withdrawal = Withdrawal.objects.create(
            user=self.user, amount=Decimal("1500.00"), status=Withdrawal.STATUS_PENDING
        )

    def test_approve_does_not_change_balance(self):
        balance_before = self.user.balance
        services.approve_withdrawal(self.withdrawal, self.admin)
        self.user.refresh_from_db()
        self.withdrawal.refresh_from_db()
        self.assertEqual(self.user.balance, balance_before)
        self.assertEqual(self.withdrawal.status, Withdrawal.STATUS_APPROVED)

    def test_reject_refunds_balance(self):
        balance_before = self.user.balance
        services.reject_withdrawal(self.withdrawal, self.admin, reason="test")
        self.user.refresh_from_db()
        self.withdrawal.refresh_from_db()
        self.assertEqual(self.user.balance, balance_before + Decimal("1500.00"))
        self.assertEqual(self.withdrawal.status, Withdrawal.STATUS_REJECTED)

    def test_double_approve_is_noop(self):
        services.approve_withdrawal(self.withdrawal, self.admin)
        w = services.approve_withdrawal(self.withdrawal, self.admin)
        self.assertEqual(w.status, Withdrawal.STATUS_APPROVED)

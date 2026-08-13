from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image

from accounts.models import User
from core.models import SiteSettings
from wallet.models import Transaction

from . import services
from .models import Investment, Plan


def make_screenshot():
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buffer, format="PNG")
    return SimpleUploadedFile("proof.png", buffer.getvalue(), content_type="image/png")


class PlanSeedTests(TestCase):
    EXPECTED = [
        (1, 10000, 1200, 60000),
        (2, 20000, 2400, 120000),
        (3, 30000, 3600, 180000),
        (4, 40000, 4800, 240000),
        (5, 50000, 6000, 300000),
        (6, 70000, 8400, 420000),
        (7, 80000, 9600, 480000),
        (8, 100000, 12000, 600000),
        (9, 120000, 14400, 720000),
        (10, 150000, 18000, 900000),
        (11, 200000, 24000, 1200000),
        (12, 300000, 36000, 1800000),
        (13, 500000, 60000, 3000000),
    ]

    def test_all_13_plans_match_the_flyer(self):
        self.assertEqual(Plan.objects.count(), 13)
        for level, price, daily_income, all_return in self.EXPECTED:
            plan = Plan.objects.get(level=level)
            self.assertEqual(plan.price, price)
            self.assertEqual(plan.daily_income, daily_income)
            self.assertEqual(plan.all_return, all_return)
            self.assertEqual(plan.duration_days, 50)


class InvestmentServiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("0700000000", "adminpass123")
        settings_obj = SiteSettings.load()
        settings_obj.fallback_referrer = self.admin
        settings_obj.save()

        self.referrer = User.objects.create_user("0788111111", "strongpass123")
        self.user = User.objects.create_user(
            "0788222222", "strongpass123", referred_by=self.referrer, is_fallback_referral=False
        )
        self.plan = Plan.objects.get(level=1)  # 10000 / 1200 daily / 50 days

    def make_pending_investment(self, user=None):
        return Investment.objects.create(
            user=user or self.user,
            plan=self.plan,
            amount=self.plan.price,
            daily_income=self.plan.daily_income,
            duration_days=self.plan.duration_days,
            payment_screenshot=make_screenshot(),
            status=Investment.STATUS_PENDING,
        )

    def test_approve_pays_welcome_bonus_and_commission_once(self):
        inv = self.make_pending_investment()
        services.approve_investment(inv, self.admin)

        self.user.refresh_from_db()
        self.referrer.refresh_from_db()
        inv.refresh_from_db()

        # welcome bonus (1000) + day-1 income (1200) = 2200
        self.assertEqual(self.user.balance, Decimal("2200.00"))
        self.assertTrue(self.user.welcome_bonus_paid)
        # 8% of 10000 = 800
        self.assertEqual(self.referrer.balance, Decimal("800.00"))
        self.assertEqual(inv.status, Investment.STATUS_APPROVED)
        self.assertEqual(inv.days_credited, 1)

        # A second investment by the same user must NOT re-pay welcome bonus or commission.
        inv2 = self.make_pending_investment()
        services.approve_investment(inv2, self.admin)
        self.user.refresh_from_db()
        self.referrer.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("3400.00"))  # +1200 day-1 income only
        self.assertEqual(self.referrer.balance, Decimal("800.00"))  # unchanged

    def test_commission_skipped_for_fallback_referral(self):
        organic_user = User.objects.create_user(
            "0788333333", "strongpass123", referred_by=self.admin, is_fallback_referral=True
        )
        inv = self.make_pending_investment(user=organic_user)
        admin_balance_before = self.admin.balance
        services.approve_investment(inv, self.admin)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.balance, admin_balance_before)

    def test_reject_causes_no_balance_change(self):
        inv = self.make_pending_investment()
        services.reject_investment(inv, self.admin, reason="bad screenshot")
        self.user.refresh_from_db()
        inv.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("0.00"))
        self.assertEqual(inv.status, Investment.STATUS_REJECTED)

    def test_double_approve_is_noop(self):
        inv = self.make_pending_investment()
        services.approve_investment(inv, self.admin)
        balance_after_first = User.objects.get(pk=self.user.pk).balance
        services.approve_investment(inv, self.admin)
        balance_after_second = User.objects.get(pk=self.user.pk).balance
        self.assertEqual(balance_after_first, balance_after_second)

    def test_credit_due_earnings_self_heals_multi_day_gap_and_caps_at_duration(self):
        inv = self.make_pending_investment()
        services.approve_investment(inv, self.admin)
        inv.refresh_from_db()

        # Simulate 10 days having elapsed since start without any crediting run.
        inv.start_date = timezone.localdate() - timedelta(days=9)
        inv.save(update_fields=["start_date"])

        services.credit_due_earnings(inv)
        inv.refresh_from_db()
        self.assertEqual(inv.days_credited, 10)
        self.assertFalse(inv.is_completed)

        # Calling again the same day must not double-credit.
        balance_before = User.objects.get(pk=self.user.pk).balance
        services.credit_due_earnings(inv)
        balance_after = User.objects.get(pk=self.user.pk).balance
        self.assertEqual(balance_before, balance_after)

        # Fast-forward past the full 50-day duration - must cap, not overcredit.
        inv.start_date = timezone.localdate() - timedelta(days=100)
        inv.save(update_fields=["start_date"])
        services.credit_due_earnings(inv)
        inv.refresh_from_db()
        self.assertEqual(inv.days_credited, 50)
        self.assertTrue(inv.is_completed)

    def test_credit_due_earnings_noop_when_not_approved(self):
        inv = self.make_pending_investment()
        services.credit_due_earnings(inv)  # still pending
        inv.refresh_from_db()
        self.assertEqual(inv.days_credited, 0)

    def test_second_pending_investment_is_blocked_by_view(self):
        self.client.force_login(self.user)
        self.make_pending_investment()
        response = self.client.post(
            f"/invest/{self.plan.id}/", {"payment_screenshot": make_screenshot()}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Investment.objects.filter(user=self.user, status=Investment.STATUS_PENDING).count(), 1
        )


class EndToEndFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("0700000000", "adminpass123")
        settings_obj = SiteSettings.load()
        settings_obj.fallback_referrer = self.admin
        settings_obj.save()

    def test_signup_invest_approve_flow(self):
        signup_resp = self.client.post(
            "/accounts/signup/",
            {
                "phone_number": "0788999999",
                "full_name": "Dana",
                "password1": "strongpass123",
                "password2": "strongpass123",
                "referral_code": "",
            },
        )
        self.assertEqual(signup_resp.status_code, 302)
        user = User.objects.get(phone_number="0788999999")
        plan = Plan.objects.get(level=1)

        invest_resp = self.client.post(
            f"/invest/{plan.id}/", {"payment_screenshot": make_screenshot()}
        )
        self.assertEqual(invest_resp.status_code, 302)
        inv = Investment.objects.get(user=user)
        self.assertEqual(inv.status, Investment.STATUS_PENDING)

        services.approve_investment(inv, self.admin)
        user.refresh_from_db()
        self.assertEqual(user.balance, Decimal("2200.00"))  # 1000 welcome + 1200 day-1
        self.assertTrue(
            Transaction.objects.filter(user=user, type=Transaction.TYPE_WELCOME_BONUS).exists()
        )

    def test_referrer_earns_commission_on_referred_users_first_approval(self):
        referrer = User.objects.create_user("0788111111", "strongpass123")
        self.client.post(
            "/accounts/signup/",
            {
                "phone_number": "0788222222",
                "full_name": "Friend",
                "password1": "strongpass123",
                "password2": "strongpass123",
                "referral_code": referrer.referral_code,
            },
        )
        friend = User.objects.get(phone_number="0788222222")
        plan = Plan.objects.get(level=2)  # 20000, 8% = 1600

        self.client.post(f"/invest/{plan.id}/", {"payment_screenshot": make_screenshot()})
        inv = Investment.objects.get(user=friend)
        services.approve_investment(inv, self.admin)

        referrer.refresh_from_db()
        self.assertEqual(referrer.balance, Decimal("1600.00"))

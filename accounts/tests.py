from django.test import TestCase
from django.urls import reverse

from core.models import SiteSettings

from .models import User, normalize_phone_number


class PhoneNumberNormalizationTests(TestCase):
    def test_accepts_local_and_international_formats(self):
        self.assertEqual(normalize_phone_number("0783108892"), "0783108892")
        self.assertEqual(normalize_phone_number("783108892"), "0783108892")
        self.assertEqual(normalize_phone_number("+250783108892"), "0783108892")
        self.assertEqual(normalize_phone_number("250783108892"), "0783108892")


class SignupReferralTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("0700000000", "adminpass123")
        settings_obj = SiteSettings.load()
        settings_obj.fallback_referrer = self.admin
        settings_obj.save()

    def test_signup_without_code_falls_back_to_admin(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "phone_number": "0788111111",
                "full_name": "Alice",
                "password1": "strongpass123",
                "password2": "strongpass123",
                "referral_code": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(phone_number="0788111111")
        self.assertEqual(user.referred_by, self.admin)
        self.assertTrue(user.is_fallback_referral)

    def test_signup_with_invalid_code_falls_back_to_admin(self):
        self.client.post(
            reverse("accounts:signup"),
            {
                "phone_number": "0788222222",
                "full_name": "Bob",
                "password1": "strongpass123",
                "password2": "strongpass123",
                "referral_code": "NOTREAL1",
            },
        )
        user = User.objects.get(phone_number="0788222222")
        self.assertEqual(user.referred_by, self.admin)
        self.assertTrue(user.is_fallback_referral)

    def test_signup_with_valid_code_sets_real_referrer(self):
        referrer = User.objects.create_user("0788333333", "strongpass123", full_name="Referrer")
        self.client.post(
            reverse("accounts:signup"),
            {
                "phone_number": "0788444444",
                "full_name": "Carol",
                "password1": "strongpass123",
                "password2": "strongpass123",
                "referral_code": referrer.referral_code,
            },
        )
        user = User.objects.get(phone_number="0788444444")
        self.assertEqual(user.referred_by, referrer)
        self.assertFalse(user.is_fallback_referral)

    def test_referral_codes_are_unique(self):
        u1 = User.objects.create_user("0788555555", "strongpass123")
        u2 = User.objects.create_user("0788666666", "strongpass123")
        self.assertNotEqual(u1.referral_code, u2.referral_code)

    def test_login_with_phone_number(self):
        User.objects.create_user("0788777777", "strongpass123")
        logged_in = self.client.login(username="0788777777", password="strongpass123")
        self.assertTrue(logged_in)

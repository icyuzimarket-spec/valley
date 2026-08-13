from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class NavbarAndAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("0700000000", "adminpass123")
        self.regular_user = User.objects.create_user("0788111111", "strongpass123")

    def test_anonymous_sees_login_and_signup(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Login")
        self.assertContains(response, "Sign Up")

    def test_regular_user_sees_profile_dashboard_countdown(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Countdown Clock")
        self.assertContains(response, "Dashboard")
        self.assertNotContains(response, "User Management")

    def test_staff_sees_management_and_admin_control(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "User Management")
        self.assertContains(response, "Admin Control")

    def test_admin_dashboard_requires_staff(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("core:admin_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_management_views_require_staff(self):
        self.client.force_login(self.regular_user)
        for name in ["core:management_users", "core:management_investments", "core:management_withdrawals"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)

    def test_dashboard_redirect_routes_by_role(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("core:dashboard_redirect"))
        self.assertRedirects(response, reverse("core:admin_dashboard"))

        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("core:dashboard_redirect"))
        self.assertRedirects(response, reverse("core:user_dashboard"))

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User

from .models import SiteSettings


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


class MaintenanceModeTests(TestCase):
    """MAINTENANCE_MODE replaces the entire site, with no way in from a browser."""

    def setUp(self):
        self.staff = User.objects.create_superuser("0700000001", "adminpass123")
        self.user = User.objects.create_user("0788111112", "strongpass123")

    @override_settings(MAINTENANCE_MODE=False)
    def test_site_serves_normally_when_switched_off(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "We are under maintenance")

    @override_settings(MAINTENANCE_MODE=True)
    def test_visitor_sees_only_the_maintenance_page(self):
        for name in ["core:home", "accounts:login", "accounts:signup"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 503)
            self.assertContains(response, "We are under maintenance", status_code=503)
            # None of the usual page furniture survives.
            self.assertNotContains(response, "navbar-valley", status_code=503)
            self.assertNotContains(response, "Sign Up", status_code=503)

    @override_settings(MAINTENANCE_MODE=True)
    def test_logged_in_user_is_blocked_too(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:user_dashboard"))
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "We are under maintenance", status_code=503)

    @override_settings(MAINTENANCE_MODE=True)
    def test_staff_are_blocked_too(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "We are under maintenance", status_code=503)

    @override_settings(MAINTENANCE_MODE=True)
    def test_django_admin_is_blocked_too(self):
        """The switch lives in code now, so the admin gets no exemption."""
        self.client.force_login(self.staff)
        for path in ["/admin/", "/admin/login/", "/admin/core/sitesettings/"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 503)
            self.assertContains(response, "We are under maintenance", status_code=503)

    @override_settings(MAINTENANCE_MODE=True, MAINTENANCE_WHATSAPP="250795927291")
    def test_maintenance_page_carries_the_whatsapp_help_link(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "https://wa.me/250795927291", status_code=503)

    @override_settings(MAINTENANCE_MODE=True, MAINTENANCE_MESSAGE="Display system down.")
    def test_message_comes_from_settings(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Display system down.", status_code=503)

    @override_settings(MAINTENANCE_MODE=True, ALLOWED_HOSTS=["healthcheck.railway.app"])
    def test_railway_healthcheck_is_not_served_a_503(self):
        response = self.client.get(reverse("core:home"), HTTP_HOST="healthcheck.railway.app")
        self.assertEqual(response.status_code, 200)

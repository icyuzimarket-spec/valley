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
    def setUp(self):
        self.settings_obj = SiteSettings.load()
        self.staff = User.objects.create_superuser("0700000001", "adminpass123")
        self.user = User.objects.create_user("0788111112", "strongpass123")

    def switch_on(self):
        self.settings_obj.maintenance_notice = True
        self.settings_obj.save()

    def test_site_serves_normally_when_switched_off(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "We are under maintenance")

    def test_visitor_sees_only_the_maintenance_page(self):
        self.switch_on()
        for name in ["core:home", "accounts:login", "accounts:signup"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 503)
            self.assertContains(response, "We are under maintenance", status_code=503)
            # None of the usual page furniture survives.
            self.assertNotContains(response, "navbar-valley", status_code=503)
            self.assertNotContains(response, "Sign Up", status_code=503)

    def test_logged_in_user_is_blocked_too(self):
        self.switch_on()
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:user_dashboard"))
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "We are under maintenance", status_code=503)

    def test_maintenance_page_carries_the_whatsapp_help_link(self):
        self.switch_on()
        self.settings_obj.maintenance_whatsapp = "250795927291"
        self.settings_obj.save()
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "https://wa.me/250795927291", status_code=503)

    def test_staff_can_still_use_the_site(self):
        self.switch_on()
        self.client.force_login(self.staff)
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maintenance mode is ON")

    def test_admin_stays_reachable_so_the_switch_can_be_turned_off(self):
        self.switch_on()
        # Anonymous: the admin login page, not the maintenance page.
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.staff)
        response = self.client.get("/admin/core/sitesettings/")
        self.assertEqual(response.status_code, 200)

    @override_settings(ALLOWED_HOSTS=["healthcheck.railway.app"])
    def test_railway_healthcheck_is_not_served_a_503(self):
        self.switch_on()
        response = self.client.get(reverse("core:home"), HTTP_HOST="healthcheck.railway.app")
        self.assertEqual(response.status_code, 200)

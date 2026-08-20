from django.conf import settings
from django.shortcuts import render

from .models import SiteSettings


class MaintenanceModeMiddleware:
    """Serve a maintenance page instead of the site while the display system is down.

    Staff and the Django admin are never blocked - somebody has to be able to
    reach Site Settings and switch maintenance mode back off.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_exempt(request) or not SiteSettings.load().maintenance_notice:
            return self.get_response(request)
        return render(
            request,
            "core/maintenance.html",
            {"site_settings": SiteSettings.load()},
            # 503 tells search engines and monitors this is temporary, so the
            # outage does not cost the site its indexed pages.
            status=503,
        )

    @staticmethod
    def _is_exempt(request):
        # The admin is the off switch, so it stays reachable - including its
        # login page, which staff need before they are authenticated.
        if request.path.startswith("/admin/"):
            return True
        # The maintenance page's own CSS, and any uploaded media it links to.
        for prefix in (settings.STATIC_URL, settings.MEDIA_URL):
            if prefix and request.path.startswith(prefix):
                return True
        # A 503 on every path would make Railway's health check fail the
        # deploy and restart the container in a loop.
        if request.get_host().startswith("healthcheck.railway.app"):
            return True
        return bool(getattr(request, "user", None) and request.user.is_staff)

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string


class MaintenanceModeMiddleware:
    """Serve the maintenance page instead of the site, for everybody.

    While ``settings.MAINTENANCE_MODE`` is on, nothing else is reachable - not
    the public pages, not a logged-in dashboard, not the Django admin. Turning
    the site back on is a code change: set MAINTENANCE_MODE = False and deploy.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.MAINTENANCE_MODE or self._is_exempt(request):
            return self.get_response(request)
        # Rendered without the request, so no context processor runs: the
        # page needs no session, no user, and - the point of it - no database.
        # It still comes up if what is broken is the database itself.
        html = render_to_string(
            "core/maintenance.html",
            {
                "maintenance_message": settings.MAINTENANCE_MESSAGE,
                "maintenance_whatsapp": settings.MAINTENANCE_WHATSAPP,
            },
        )
        # 503 tells search engines and monitors this is temporary, so the
        # outage does not cost the site its indexed pages.
        return HttpResponse(html, status=503)

    @staticmethod
    def _is_exempt(request):
        """Only what the maintenance page itself needs to work.

        Neither of these serves site content, so nobody gets in through them.
        """
        # The page's own CSS, and any uploaded media it links to.
        for prefix in (settings.STATIC_URL, settings.MEDIA_URL):
            if prefix and request.path.startswith(prefix):
                return True
        # A 503 on every path would make Railway's health check fail the
        # deploy and restart the container in a loop.
        return request.get_host().startswith("healthcheck.railway.app")

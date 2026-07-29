from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class AISearchRateThrottle(SimpleRateThrottle):
    """Apply separate, non-overlapping quotas to guests and signed-in users."""

    rate = "10/minute"
    anon_scope = "ai_anonymous"
    authenticated_scope = "ai_authenticated"

    def allow_request(self, request, view):
        self.scope = (
            self.authenticated_scope
            if request.user and request.user.is_authenticated
            else self.anon_scope
        )
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        default_rate = "30/minute" if self.scope == self.authenticated_scope else "10/minute"
        self.rate = rates.get(self.scope, default_rate)
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = str(request.user.pk)
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class UserOrAnonymousRateThrottle(SimpleRateThrottle):
    """Use configurable, non-overlapping quotas for guests and signed-in users."""

    anon_scope = ""
    authenticated_scope = ""
    anon_default_rate = "10/minute"
    authenticated_default_rate = "30/minute"

    def get_rate(self):
        # DRF resolves a provisional rate before request identity is available.
        return self.anon_default_rate

    def allow_request(self, request, view):
        self.scope = (
            self.authenticated_scope
            if request.user and request.user.is_authenticated
            else self.anon_scope
        )
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        default_rate = (
            self.authenticated_default_rate
            if self.scope == self.authenticated_scope
            else self.anon_default_rate
        )
        self.rate = rates.get(self.scope, default_rate)
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = str(request.user.pk)
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AISearchRateThrottle(UserOrAnonymousRateThrottle):
    anon_scope = "ai_search_anonymous"
    authenticated_scope = "ai_search_authenticated"


class AIRecommendationRateThrottle(UserOrAnonymousRateThrottle):
    anon_scope = "ai_recommendation_anonymous"
    authenticated_scope = "ai_recommendation_authenticated"
    anon_default_rate = "30/minute"
    authenticated_default_rate = "60/minute"


class RecommendationEventRateThrottle(UserOrAnonymousRateThrottle):
    anon_scope = "ai_recommendation_event_anonymous"
    authenticated_scope = "ai_recommendation_event_authenticated"
    anon_default_rate = "120/minute"
    authenticated_default_rate = "300/minute"

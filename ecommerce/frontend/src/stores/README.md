# Global stores

Cross-feature Pinia stores live here. `auth.ts` keeps the short-lived access token in memory,
restores a session through the HttpOnly refresh cookie, and exposes the authenticated user to
router guards and account pages.

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import SignInView

app_name = "authentication"

urlpatterns = [
    # ── Sign-in ───────────────────────────────────────────────────────────────
    # POST  { email, password } → { id, email, access, refresh }
    path("signin/", SignInView.as_view(), name="signin"),

    # ── Token utilities (simplejwt) ───────────────────────────────────────────
    # POST  { refresh } → { access }          — get a new access token
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # POST  { token }   → 200 / 401           — verify any token is still valid
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

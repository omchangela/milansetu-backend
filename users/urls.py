from django.urls import path

from .views import SignupView

app_name = "users"

urlpatterns = [
    # POST  — register a new user, returns JWT tokens
    # GET   — returns CSRF cookie / token for the client
    path("signup/", SignupView.as_view(), name="signup"),
]

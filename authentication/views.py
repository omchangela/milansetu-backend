from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class SignInView(APIView):
    """
    POST /api/auth/signin/

    Authenticates a user with email + password and returns a JWT token pair.

    Request body:
        { "email": "user@example.com", "password": "secret123" }

    Response 200:
        { "id": 1, "email": "...", "access": "...", "refresh": "..." }

    Response 401:
        { "detail": "Invalid credentials." }
    """

    # authentication_classes = [] is critical here.
    # DRF runs authentication BEFORE checking permissions, so even with
    # permission_classes = [AllowAny], if JWTAuthentication sees a stale
    # token in the Authorization header it raises "Token is invalid" and
    # the view never runs. Setting authentication_classes = [] disables
    # that check entirely for this public endpoint.
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "This account is inactive."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "id":      user.id,
                "email":   user.email,
                "user_type":    user.user_type,
                "is_premium":   user.is_premium,
                "is_staff":     user.is_staff,
                "access":  str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )

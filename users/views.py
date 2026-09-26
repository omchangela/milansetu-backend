from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import SignupSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SignupView(APIView):
    """
    POST /api/users/signup/ — Registers a new user, returns JWT tokens.
    """

    # No authentication — public endpoint.
    # Prevents JWTAuthentication from rejecting requests with stale tokens.
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        # Generate JWT tokens for the newly created user
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )

    def get(self, request):
        """
        GET /api/users/signup/

        Returns a CSRF cookie so frontend clients can obtain the token
        before submitting the signup form.
        """
        return Response(
            {"csrfToken": get_token(request)},
            status=status.HTTP_200_OK,
        )

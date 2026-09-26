"""Gallery API views."""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .gallery_service import (
    BASIC_GALLERY_LIMIT,
    PREMIUM_GALLERY_LIMIT,
    can_upload_more,
    gallery_limit_for_user,
    save_gallery_image,
    set_profile_photo,
)
from .models import UserGallery
from .serializers import UserGallerySerializer


class UserGalleryListView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        items = UserGallery.objects.filter(user=request.user)
        return Response(
            {
                "items": UserGallerySerializer(items, many=True).data,
                "limit": gallery_limit_for_user(request.user),
                "count": items.filter(
                    sensitivity_status__in=[
                        UserGallery.SensitivityStatus.APPROVED,
                        UserGallery.SensitivityStatus.PENDING,
                    ]
                ).count(),
                "basic_limit": BASIC_GALLERY_LIMIT,
                "premium_limit": PREMIUM_GALLERY_LIMIT,
                "is_premium": request.user.is_premium,
            }
        )

    def post(self, request):
        uploaded = request.FILES.get("image") or request.FILES.get("profile_photo")
        if not uploaded:
            return Response(
                {"detail": "No image file provided. Use field name 'image'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        set_as_profile = request.data.get("set_as_profile", "false").lower() in (
            "true",
            "1",
            "yes",
        )

        try:
            item = save_gallery_image(
                request.user,
                uploaded,
                set_as_profile=set_as_profile,
            )
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_402_PAYMENT_REQUIRED if "Premium" in msg or "Upgrade" in msg else status.HTTP_400_BAD_REQUEST
            return Response(
                {"detail": msg, "upgrade_required": "Premium" in msg or "Upgrade" in msg},
                status=code,
            )

        return Response(
            UserGallerySerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class UserGalleryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_owned(self, request, pk):
        try:
            return UserGallery.objects.get(pk=pk, user=request.user)
        except UserGallery.DoesNotExist:
            return None

    def delete(self, request, pk):
        item = self._get_owned(request, pk)
        if not item:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        was_profile = item.is_profile_photo
        item_id = item.id
        item.delete()

        if was_profile:
            from .models import ProfileDetails

            profile = ProfileDetails.objects.filter(user=request.user).first()
            if profile and profile.profile_photo_id == item_id:
                profile.profile_photo = None
                profile.save(update_fields=["profile_photo"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserGallerySetProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            item = UserGallery.objects.get(pk=pk, user=request.user)
        except UserGallery.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            set_profile_photo(request.user, item)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(UserGallerySerializer(item).data)


class UserGalleryImageView(APIView):
    """Serve binary image data from the database."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            item = UserGallery.objects.get(pk=pk)
        except UserGallery.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if item.user_id != request.user.id and not request.user.is_staff:
            if item.sensitivity_status != UserGallery.SensitivityStatus.APPROVED:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        return HttpResponse(
            bytes(item.image_data),
            content_type=item.content_type or "image/jpeg",
        )

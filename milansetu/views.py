from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import SignupSerializer

from .gallery_service import save_gallery_image
from .matching import (
    apply_employee_filters,
    calculate_compatibility,
    filter_profiles_for_user,
)
from .models import IdealPartner, ProfileDetails, SentInterest, FCMToken, ProfileView
from .premium import (
    can_edit_profile,
    check_premium_ideal_partner_fields,
    get_account_meta,
    increment_profile_edit_count,
)
from .serializers import (
    IdealPartnerSerializer,
    ProfileDetailsSerializer,
    SentInterestCreateSerializer,
    SentInterestSerializer,
)


def _get_or_create_ideal_partner(user) -> IdealPartner:
    ideal, _ = IdealPartner.objects.get_or_create(user=user)
    return ideal


def _account_response(user, profile=None, ideal=None) -> dict:
    return {
        "profile": ProfileDetailsSerializer(profile).data if profile else None,
        "ideal_partner": IdealPartnerSerializer(ideal).data if ideal else None,
        "account": get_account_meta(user),
    }


# ─── Signup ───────────────────────────────────────────────────────────────────

@method_decorator(ensure_csrf_cookie, name="dispatch")
class SignupView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        return Response({"csrfToken": get_token(request)}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        uploaded = request.FILES.get("profile_photo") or request.FILES.get("image")
        if uploaded:
            try:
                save_gallery_image(user, uploaded, set_as_profile=True)
            except ValueError as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "user_type": user.user_type,
                "is_premium": user.is_premium,
                "is_staff": user.is_staff,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


# ─── My Profile + Ideal Partner ───────────────────────────────────────────────

class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_profile(self, user):
        try:
            return ProfileDetails.objects.get(user=user)
        except ProfileDetails.DoesNotExist:
            return None

    def get(self, request):
        profile = self._get_profile(request.user)
        ideal = IdealPartner.objects.filter(user=request.user).first()
        if profile is None:
            return Response(
                {
                    **_account_response(request.user, profile=None, ideal=ideal),
                    "detail": "Profile not found. Use PATCH to create one.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(_account_response(request.user, profile=profile, ideal=ideal))

    def patch(self, request):
        allowed, error_msg = can_edit_profile(request.user)
        if not allowed:
            return Response(
                {"detail": error_msg, "upgrade_required": True},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        profile = self._get_profile(request.user)
        if profile is None:
            serializer = ProfileDetailsSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            profile = serializer.save(user=request.user)
            increment_profile_edit_count(request.user)
        else:
            serializer = ProfileDetailsSerializer(profile, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            profile = serializer.save()
            increment_profile_edit_count(request.user)

        ideal = _get_or_create_ideal_partner(request.user)
        return Response(_account_response(request.user, profile=profile, ideal=ideal))

    def put(self, request):
        return self.patch(request)


class IdealPartnerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ideal = IdealPartner.objects.filter(user=request.user).first()
        if ideal is None:
            return Response(
                {"detail": "No ideal partner preferences yet. Use PATCH to set them."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "ideal_partner": IdealPartnerSerializer(ideal).data,
                "account": get_account_meta(request.user),
            }
        )

    def patch(self, request):
        ideal = _get_or_create_ideal_partner(request.user)
        payload, blocked, premium_error = check_premium_ideal_partner_fields(
            request.user, request.data
        )

        if premium_error:
            return Response(
                {
                    "detail": premium_error,
                    "upgrade_required": True,
                    "premium_fields": blocked,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        serializer = IdealPartnerSerializer(ideal, data=payload, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        ideal = serializer.save()
        return Response(
            {
                "ideal_partner": IdealPartnerSerializer(ideal).data,
                "account": get_account_meta(request.user),
            }
        )


# ─── Profile discovery (role-based) ─────────────────────────────────────────

class ProfileDetailsListView(APIView):
    """
    GET /api/milansetu/profiles/

    - user: profiles matching ideal partner preferences (sorted by score)
    - employee/admin: all profiles with optional query filters
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        base_qs = (
            ProfileDetails.objects.filter(user__isnull=False)
            .exclude(user=request.user)
            .select_related("user")
        )

        if request.user.is_employee:
            profiles = list(apply_employee_filters(base_qs, request.query_params))
            data = []
            for profile in profiles:
                row = ProfileDetailsSerializer(profile).data
                row["match_score"] = calculate_compatibility(
                    IdealPartner.objects.filter(user=request.user).first(),
                    profile,
                )
                row["user_type"] = profile.user.user_type
                data.append(row)
            return Response(data)

        ideal = IdealPartner.objects.filter(user=request.user).first()
        scored = filter_profiles_for_user(base_qs, ideal)
        data = []
        for profile, score in scored:
            row = ProfileDetailsSerializer(profile).data
            row["match_score"] = score
            data.append(row)
        return Response(data)

    def post(self, request):
        if not request.user.is_superuser:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ProfileDetailsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProfileDetailsDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk):
        try:
            return ProfileDetails.objects.select_related("user").get(pk=pk)
        except ProfileDetails.DoesNotExist:
            return None

    def get(self, request, pk):
        profile = self._get_object(pk)
        if not profile:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if profile.user_id == request.user.id:
            return Response(ProfileDetailsSerializer(profile).data)

        if request.user.is_employee:
            row = ProfileDetailsSerializer(profile).data
            row["match_score"] = calculate_compatibility(
                IdealPartner.objects.filter(user=request.user).first(),
                profile,
            )
            row["user_type"] = profile.user.user_type
            ideal = IdealPartner.objects.filter(user=profile.user).first()
            if ideal:
                row["ideal_partner"] = IdealPartnerSerializer(ideal).data
            return Response(row)

        ideal = IdealPartner.objects.filter(user=request.user).first()
        score = calculate_compatibility(ideal, profile)
        if score < 60:
            return Response({"detail": "Profile not in your match list."}, status=status.HTTP_403_FORBIDDEN)

        row = ProfileDetailsSerializer(profile).data
        row["match_score"] = score
        ideal = IdealPartner.objects.filter(user=profile.user).first()
        if ideal:
            row["ideal_partner"] = IdealPartnerSerializer(ideal).data
        return Response(row)

    def patch(self, request, pk):
        profile = self._get_object(pk)
        if not profile or profile.user_id != request.user.id:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        allowed, error_msg = can_edit_profile(request.user)
        if not allowed:
            return Response(
                {"detail": error_msg, "upgrade_required": True},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        serializer = ProfileDetailsSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        profile = serializer.save()
        increment_profile_edit_count(request.user)
        return Response(ProfileDetailsSerializer(profile).data)

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        if not request.user.is_superuser:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        profile = self._get_object(pk)
        if not profile:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Profile View Tracking ────────────────────────────────────────────────────

class ProfileViewRecordView(APIView):
    """
    POST /api/milansetu/profiles/<pk>/view/
    Records that the logged-in user viewed this profile.
    Uses update_or_create so repeated views just refresh the timestamp.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            viewed_profile = ProfileDetails.objects.get(pk=pk)
        except ProfileDetails.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Don't record self-views
        if viewed_profile.user_id == request.user.id:
            return Response({"detail": "Self-view ignored."}, status=status.HTTP_200_OK)

        # Use raw update to refresh viewed_at since auto_now_add won't update
        from django.utils import timezone
        obj, created = ProfileView.objects.get_or_create(
            viewer=request.user,
            viewed_profile=viewed_profile,
        )
        if not created:
            # Refresh the timestamp manually
            ProfileView.objects.filter(pk=obj.pk).update(viewed_at=timezone.now())

        return Response({"recorded": True}, status=status.HTTP_200_OK)


class MyRecentViewsView(APIView):
    """
    GET /api/milansetu/profiles/views/
    Returns the profiles that the logged-in user recently viewed (most recent first).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        views = (
            ProfileView.objects.filter(viewer=request.user)
            .select_related("viewed_profile")
            .order_by("-viewed_at")[:20]
        )
        data = []
        for v in views:
            p = v.viewed_profile
            data.append({
                "viewed_profile_id": p.id,
                "full_name": p.full_name or "Member",
                "age": p.age,
                "current_designation": p.current_designation,
                "education": p.education,
                "birth_place": p.birth_place,
                "profile_photo_url": (
                    f"/api/milansetu/gallery/{p.profile_photo_id}/image/"
                    if p.profile_photo_id else None
                ),
                "viewed_at": v.viewed_at,
            })
        return Response(data)


# ─── Sent Interests ───────────────────────────────────────────────────────────

class SentInterestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        interests = (
            SentInterest.objects.filter(sender=request.user)
            .select_related("receiver_profile")
            .order_by("-created_at")
        )
        return Response(SentInterestSerializer(interests, many=True).data)

    def post(self, request):
        serializer = SentInterestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        receiver_id = serializer.validated_data["receiver_profile_id"]
        try:
            receiver_profile = ProfileDetails.objects.select_related("user").get(pk=receiver_id)
        except ProfileDetails.DoesNotExist:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        if receiver_profile.user_id == request.user.id:
            return Response({"detail": "Cannot send interest to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        if SentInterest.objects.filter(
            sender=request.user,
            receiver_profile=receiver_profile,
        ).exists():
            return Response({"detail": "Interest already sent."}, status=status.HTTP_400_BAD_REQUEST)

        ideal = IdealPartner.objects.filter(user=request.user).first()
        score = calculate_compatibility(ideal, receiver_profile)

        interest = SentInterest.objects.create(
            sender=request.user,
            receiver_profile=receiver_profile,
            message=serializer.validated_data.get("message", ""),
            match_score=score,
        )

        # Send FCM push notification to the receiver
        try:
            from .fcm_service import send_interest_notification
            send_interest_notification(sender=request.user, receiver=receiver_profile.user)
        except Exception:
            pass  # Never block interest creation on notification failure

        return Response(
            SentInterestSerializer(interest).data,
            status=status.HTTP_201_CREATED,
        )


class SentInterestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_interest(self, request, pk):
        try:
            return SentInterest.objects.select_related("receiver_profile").get(
                pk=pk,
                sender=request.user,
            )
        except SentInterest.DoesNotExist:
            return None

    def patch(self, request, pk):
        interest = self._get_interest(request, pk)
        if not interest:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if action == "withdraw":
            if interest.status != SentInterest.Status.PENDING:
                return Response(
                    {"detail": "Only pending interests can be withdrawn."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            interest.status = SentInterest.Status.WITHDRAWN
            interest.save(update_fields=["status", "updated_at"])
            return Response(SentInterestSerializer(interest).data)

        return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        interest = self._get_interest(request, pk)
        if not interest:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        interest.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SentInterestStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = SentInterest.objects.filter(sender=request.user)
        total = qs.count()
        accepted = qs.filter(status=SentInterest.Status.ACCEPTED).count()
        pending = qs.filter(status=SentInterest.Status.PENDING).count()
        declined = qs.filter(status=SentInterest.Status.DECLINED).count()
        response_rate = round((accepted / total) * 100) if total else 0
        return Response(
            {
                "total": total,
                "accepted": accepted,
                "pending": pending,
                "declined": declined,
                "response_rate": response_rate,
            }
        )


# ─── Received Interests ──────────────────────────────────────────────────────────

class ReceivedInterestListView(APIView):
    """
    GET /api/milansetu/interests/received/
    Returns interests where the current user is the receiver.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            my_profile = ProfileDetails.objects.get(user=request.user)
        except ProfileDetails.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        interests = (
            SentInterest.objects.filter(receiver_profile=my_profile)
            .select_related("sender", "sender__profile")
            .order_by("-created_at")
        )
        data = []
        for interest in interests:
            sender_profile = getattr(interest.sender, 'profile', None)
            data.append({
                "id": interest.id,
                "sender_id": interest.sender_id,
                "sender_name": sender_profile.full_name if sender_profile else interest.sender.email,
                "sender_profile": ProfileDetailsSerializer(sender_profile).data if sender_profile else None,
                "status": interest.status,
                "message": interest.message,
                "match_score": interest.match_score,
                "created_at": interest.created_at,
            })
        return Response(data)

    def patch(self, request):
        """Accept or decline a received interest."""
        interest_id = request.data.get("interest_id")
        action = request.data.get("action")  # 'accept' | 'decline'
        if not interest_id or action not in ("accept", "decline"):
            return Response({"detail": "Provide interest_id and action (accept/decline)."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            my_profile = ProfileDetails.objects.get(user=request.user)
            interest = SentInterest.objects.get(pk=interest_id, receiver_profile=my_profile)
        except (ProfileDetails.DoesNotExist, SentInterest.DoesNotExist):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if interest.status != SentInterest.Status.PENDING:
            return Response({"detail": "Interest is no longer pending."}, status=status.HTTP_400_BAD_REQUEST)

        interest.status = (
            SentInterest.Status.ACCEPTED if action == "accept"
            else SentInterest.Status.DECLINED
        )
        interest.save(update_fields=["status", "updated_at"])

        # Send push notification on acceptance
        if interest.status == SentInterest.Status.ACCEPTED:
            try:
                from .fcm_service import send_interest_accepted_notification
                send_interest_accepted_notification(sender=request.user, receiver=interest.sender)
            except Exception:
                pass

        return Response(SentInterestSerializer(interest).data)



class AcceptedInterestsView(APIView):
    """
    GET /api/milansetu/interests/accepted/
    Returns all accepted interests (sent or received) — used to populate the chat contact list.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Interests this user sent that were accepted
        sent_accepted = (
            SentInterest.objects.filter(sender=user, status=SentInterest.Status.ACCEPTED)
            .select_related("receiver_profile", "receiver_profile__user")
        )

        # Interests this user received that they accepted
        try:
            my_profile = ProfileDetails.objects.get(user=user)
            received_accepted = (
                SentInterest.objects.filter(
                    receiver_profile=my_profile,
                    status=SentInterest.Status.ACCEPTED
                ).select_related("sender", "sender__profile")
            )
        except ProfileDetails.DoesNotExist:
            received_accepted = SentInterest.objects.none()

        contacts = []

        for interest in sent_accepted:
            other_profile = interest.receiver_profile
            other_user = other_profile.user
            contacts.append({
                "interest_id": interest.id,
                "direction": "sent",
                "other_user_id": other_user.id,
                "other_user_email": other_user.email,
                "profile": ProfileDetailsSerializer(other_profile).data,
                "match_score": interest.match_score,
                "connected_at": interest.updated_at,
            })

        for interest in received_accepted:
            sender = interest.sender
            sender_profile = getattr(sender, 'profile', None)
            contacts.append({
                "interest_id": interest.id,
                "direction": "received",
                "other_user_id": sender.id,
                "other_user_email": sender.email,
                "profile": ProfileDetailsSerializer(sender_profile).data if sender_profile else None,
                "match_score": interest.match_score,
                "connected_at": interest.updated_at,
            })

        return Response(contacts)


# ─── FCM Token ───────────────────────────────────────────────────────────────────

class FCMTokenView(APIView):
    """
    POST /api/milansetu/fcm/token/
    Store or update the FCM registration token for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("token", "").strip()
        if not token:
            return Response({"detail": "token is required."}, status=status.HTTP_400_BAD_REQUEST)

        FCMToken.objects.update_or_create(
            user=request.user,
            defaults={"token": token},
        )
        return Response({"detail": "Token saved."}, status=status.HTTP_200_OK)

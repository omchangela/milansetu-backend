from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from milansetu.models import IdealPartner, ProfileDetails

User = get_user_model()


class SignupSerializer(serializers.Serializer):
    """
    Registers a new user.

    Required : email, password, confirm_password
    Optional : phone + all profile_details fields
    """

    # ── Credentials ───────────────────────────────────────────────────────────
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    # ── profile_details fields (all optional at signup) ───────────────────────
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    age = serializers.IntegerField(required=False, allow_null=True)
    height_cm = serializers.IntegerField(required=False, allow_null=True)
    religion = serializers.CharField(max_length=100, required=False, allow_blank=True)
    mother_tongue = serializers.CharField(max_length=100, required=False, allow_blank=True)
    marital_status = serializers.CharField(max_length=100, required=False, allow_blank=True)
    father_occupation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    mother_occupation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    siblings_count = serializers.IntegerField(required=False, allow_null=True)
    siblings_details = serializers.CharField(required=False, allow_blank=True)
    family_values = serializers.CharField(max_length=255, required=False, allow_blank=True)
    industry = serializers.CharField(max_length=255, required=False, allow_blank=True)
    education = serializers.CharField(max_length=255, required=False, allow_blank=True)
    current_designation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    current_company = serializers.CharField(max_length=255, required=False, allow_blank=True)
    annual_income_min = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    annual_income_max = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    income_unit = serializers.CharField(max_length=20, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    time_of_birth = serializers.TimeField(required=False, allow_null=True)
    birth_place = serializers.CharField(max_length=255, required=False, allow_blank=True)
    zodiac_sign = serializers.CharField(max_length=100, required=False, allow_blank=True)
    manglik_status = serializers.CharField(max_length=50, required=False, allow_blank=True)
    kundali_url = serializers.CharField(max_length=500, required=False, allow_blank=True)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone(self, value):
        if value and User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    # ── Create ────────────────────────────────────────────────────────────────

    _USER_FIELDS = {"email", "password", "phone"}

    def create(self, validated_data):
        # Split user credentials from profile fields
        user_data = {k: validated_data.pop(k) for k in list(self._USER_FIELDS) if k in validated_data}
        profile_data = validated_data  # remaining fields go to profile_details

        with transaction.atomic():
            user = User.objects.create_user(
                email=user_data["email"],
                password=user_data["password"],
                phone=user_data.get("phone"),
            )
            ProfileDetails.objects.create(user=user, **profile_data)
            IdealPartner.objects.create(user=user)

        return user

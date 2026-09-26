from rest_framework import serializers

from .models import IdealPartner, ProfileDetails, SentInterest, UserGallery


class ProfileDetailsSerializer(serializers.ModelSerializer):
    match_score = serializers.IntegerField(read_only=True, required=False)
    profile_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ProfileDetails
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at", "profile_photo")

    def get_profile_photo_url(self, obj):
        if obj.profile_photo_id:
            return f"/api/milansetu/gallery/{obj.profile_photo_id}/image/"
        return None


class UserGallerySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = UserGallery
        fields = (
            "id",
            "content_type",
            "original_filename",
            "file_size",
            "width",
            "height",
            "sensitivity_status",
            "sensitivity_score",
            "sensitivity_message",
            "is_profile_photo",
            "created_at",
            "image_url",
        )
        read_only_fields = fields

    def get_image_url(self, obj):
        return f"/api/milansetu/gallery/{obj.id}/image/"


class IdealPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdealPartner
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at")


class SentInterestSerializer(serializers.ModelSerializer):
    receiver = ProfileDetailsSerializer(source="receiver_profile", read_only=True)

    class Meta:
        model = SentInterest
        fields = (
            "id",
            "sender",
            "receiver_profile",
            "receiver",
            "status",
            "message",
            "response_message",
            "match_score",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "sender",
            "status",
            "response_message",
            "match_score",
            "created_at",
            "updated_at",
        )


class SentInterestCreateSerializer(serializers.Serializer):
    receiver_profile_id = serializers.IntegerField()
    message = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class AccountMetaSerializer(serializers.Serializer):
    user_type = serializers.CharField()
    is_premium = serializers.BooleanField()
    is_staff = serializers.BooleanField()
    profile_edits_remaining = serializers.IntegerField(allow_null=True)
    free_profile_edits_per_month = serializers.IntegerField()
    basic_ideal_partner_fields = serializers.ListField(child=serializers.CharField())
    premium_ideal_partner_fields = serializers.ListField(child=serializers.CharField())
    profile_photo_url = serializers.CharField(allow_null=True)
    gallery_limit = serializers.IntegerField()
    gallery_count = serializers.IntegerField()
    basic_gallery_limit = serializers.IntegerField()
    premium_gallery_limit = serializers.IntegerField()


class MyAccountSerializer(serializers.Serializer):
    profile = ProfileDetailsSerializer()
    ideal_partner = IdealPartnerSerializer(allow_null=True)
    account = AccountMetaSerializer()

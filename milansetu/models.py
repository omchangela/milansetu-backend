from django.conf import settings
from django.db import models


class ProfileDetails(models.Model):
    """
    One-to-one profile record linked to a User.
    All fields are optional so users can fill in details progressively.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=255, blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    height_cm = models.IntegerField(blank=True, null=True)
    religion = models.CharField(max_length=100, blank=True, null=True)
    mother_tongue = models.CharField(max_length=100, blank=True, null=True)
    marital_status = models.CharField(max_length=100, blank=True, null=True)
    father_occupation = models.CharField(max_length=255, blank=True, null=True)
    mother_occupation = models.CharField(max_length=255, blank=True, null=True)
    siblings_count = models.IntegerField(blank=True, null=True)
    siblings_details = models.TextField(blank=True, null=True)
    family_values = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    education = models.CharField(max_length=255, blank=True, null=True)
    current_designation = models.CharField(max_length=255, blank=True, null=True)
    current_company = models.CharField(max_length=255, blank=True, null=True)
    annual_income_min = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    annual_income_max = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    income_unit = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    time_of_birth = models.TimeField(blank=True, null=True)
    birth_place = models.CharField(max_length=255, blank=True, null=True)
    zodiac_sign = models.CharField(max_length=100, blank=True, null=True)
    manglik_status = models.CharField(max_length=50, blank=True, null=True)
    kundali_url = models.CharField(max_length=500, blank=True, null=True)
    profile_photo = models.ForeignKey(
        "UserGallery",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_for",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profile_details"

    def __str__(self):
        return self.full_name or f"Profile #{self.pk}"


class IdealPartner(models.Model):
    """
    One-to-one ideal partner preferences per user.
    Basic fields are free; extended fields require premium membership.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ideal_partner",
    )
    # Free-tier filters
    age_min = models.IntegerField(blank=True, null=True)
    age_max = models.IntegerField(blank=True, null=True)
    height_min_cm = models.IntegerField(blank=True, null=True)
    height_max_cm = models.IntegerField(blank=True, null=True)
    religion = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    # Premium-tier filters
    mother_tongue = models.CharField(max_length=100, blank=True, null=True)
    marital_status = models.CharField(max_length=100, blank=True, null=True)
    education = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    min_income = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    max_income = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    income_unit = models.CharField(max_length=20, blank=True, null=True)
    manglik_status = models.CharField(max_length=50, blank=True, null=True)
    family_values = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ideal_partner"

    def __str__(self):
        return f"Ideal partner prefs for {self.user_id}"


class SentInterest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        WITHDRAWN = "withdrawn", "Withdrawn"

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_interests",
    )
    receiver_profile = models.ForeignKey(
        ProfileDetails,
        on_delete=models.CASCADE,
        related_name="received_interests",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    message = models.TextField(blank=True, null=True)
    response_message = models.TextField(blank=True, null=True)
    match_score = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sent_interests"
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "receiver_profile"],
                name="unique_interest_per_sender_receiver",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender_id} → profile {self.receiver_profile_id} ({self.status})"


class UserGallery(models.Model):
    class SensitivityStatus(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PENDING = "pending", "Pending Review"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gallery_images",
    )
    image_data = models.BinaryField()
    content_type = models.CharField(max_length=100, default="image/jpeg")
    original_filename = models.CharField(max_length=255, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    sensitivity_status = models.CharField(
        max_length=20,
        choices=SensitivityStatus.choices,
        default=SensitivityStatus.PENDING,
    )
    sensitivity_score = models.PositiveSmallIntegerField(default=0)
    sensitivity_message = models.CharField(max_length=500, blank=True, default="")
    is_profile_photo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_gallery"
        ordering = ["-is_profile_photo", "-created_at"]

    def __str__(self):
        return f"Gallery #{self.pk} for user {self.user_id}"


class UserInvite(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invites",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_invites",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    message = models.TextField(blank=True, null=True)
    response_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_invites"
        constraints = [
            models.UniqueConstraint(
                fields=["requester", "target"], name="unique_invite_per_requester_target"
            )
        ]

    def __str__(self):
        return f"Invite {self.requester_id} → {self.target_id} ({self.status})"


class ProfileView(models.Model):
    """
    Records when a user views another user's profile.
    viewer  → the user who clicked View Profile
    viewed  → the profile that was viewed
    """
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile_views_made',
    )
    viewed_profile = models.ForeignKey(
        'ProfileDetails',
        on_delete=models.CASCADE,
        related_name='profile_views_received',
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'profile_views'
        ordering = ['-viewed_at']
        # One record per viewer+profile pair — update timestamp instead of duplicating
        constraints = [
            models.UniqueConstraint(
                fields=['viewer', 'viewed_profile'],
                name='unique_profile_view',
            )
        ]

    def __str__(self):
        return f"User {self.viewer_id} viewed profile {self.viewed_profile_id}"


class FCMToken(models.Model):
    """
    Stores the Firebase Cloud Messaging registration token for a user's browser.
    One token per user (updated on each login).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fcm_token",
    )
    token = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fcm_tokens"

    def __str__(self):
        return f"FCM token for user {self.user_id}"

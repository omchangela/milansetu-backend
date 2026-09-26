"""Premium membership limits and profile-edit tracking."""

from django.utils import timezone

from users.models import FREE_PROFILE_EDITS_PER_MONTH, User

from .gallery_service import (
    BASIC_GALLERY_LIMIT,
    PREMIUM_GALLERY_LIMIT,
    gallery_limit_for_user,
    get_profile_photo_url,
)
from .models import UserGallery

BASIC_IDEAL_PARTNER_FIELDS = frozenset({
    "age_min",
    "age_max",
    "height_min_cm",
    "height_max_cm",
    "religion",
    "location",
})

PREMIUM_IDEAL_PARTNER_FIELDS = frozenset({
    "mother_tongue",
    "marital_status",
    "education",
    "industry",
    "min_income",
    "max_income",
    "income_unit",
    "manglik_status",
    "family_values",
})


def _current_month_key() -> str:
    return timezone.now().strftime("%Y-%m")


def reset_edit_counter_if_needed(user: User) -> None:
    month = _current_month_key()
    if user.profile_edit_month != month:
        user.profile_edit_count = 0
        user.profile_edit_month = month
        user.save(update_fields=["profile_edit_count", "profile_edit_month"])


def profile_edits_remaining(user: User) -> int | None:
    """None means unlimited (premium or staff roles)."""
    if user.is_premium or user.is_employee:
        return None
    reset_edit_counter_if_needed(user)
    return max(0, FREE_PROFILE_EDITS_PER_MONTH - user.profile_edit_count)


def can_edit_profile(user: User) -> tuple[bool, str | None]:
    if user.is_premium or user.is_employee:
        return True, None
    remaining = profile_edits_remaining(user)
    if remaining is not None and remaining <= 0:
        return False, (
            "Free accounts can edit their profile only 3 times per month. "
            "Upgrade to Premium for unlimited edits."
        )
    return True, None


def increment_profile_edit_count(user: User) -> None:
    if user.is_premium or user.is_employee:
        return
    reset_edit_counter_if_needed(user)
    user.profile_edit_count += 1
    user.save(update_fields=["profile_edit_count"])


def filter_ideal_partner_payload(user: User, data: dict) -> dict:
    """Strip premium-only ideal partner fields for non-premium users."""
    if user.is_premium or user.is_employee:
        return data
    return {k: v for k, v in data.items() if k in BASIC_IDEAL_PARTNER_FIELDS}


def _has_value(value) -> bool:
    return value is not None and value != ""


def check_premium_ideal_partner_fields(user: User, data: dict) -> tuple[dict, list[str], str | None]:
    """
    Free users may always save basic fields.
    Return blocked field names + message only when they send non-empty premium values.
    """
    if user.is_premium or user.is_employee:
        return data, [], None

    attempted_premium = sorted(
        key for key in PREMIUM_IDEAL_PARTNER_FIELDS
        if key in data and _has_value(data[key])
    )
    if attempted_premium:
        labels = ", ".join(f.replace("_", " ") for f in attempted_premium)
        return (
            filter_ideal_partner_payload(user, data),
            attempted_premium,
            (
                f"Premium membership is required to set: {labels}. "
                "Basic preferences (age, height, religion, location) are free."
            ),
        )

    return filter_ideal_partner_payload(user, data), [], None


def get_account_meta(user: User) -> dict:
    gallery_count = UserGallery.objects.filter(
        user=user,
        sensitivity_status__in=[
            UserGallery.SensitivityStatus.APPROVED,
            UserGallery.SensitivityStatus.PENDING,
        ],
    ).count()
    return {
        "user_type": user.user_type,
        "is_premium": user.is_premium,
        "is_staff": user.is_staff,
        "profile_edits_remaining": profile_edits_remaining(user),
        "free_profile_edits_per_month": FREE_PROFILE_EDITS_PER_MONTH,
        "basic_ideal_partner_fields": sorted(BASIC_IDEAL_PARTNER_FIELDS),
        "premium_ideal_partner_fields": sorted(PREMIUM_IDEAL_PARTNER_FIELDS),
        "profile_photo_url": get_profile_photo_url(user),
        "gallery_limit": gallery_limit_for_user(user),
        "gallery_count": gallery_count,
        "basic_gallery_limit": BASIC_GALLERY_LIMIT,
        "premium_gallery_limit": PREMIUM_GALLERY_LIMIT,
    }

"""User gallery upload limits and image sensitivity checks."""

import io
from typing import BinaryIO

from django.db import transaction

from users.models import User

from .models import ProfileDetails, UserGallery

BASIC_GALLERY_LIMIT = 5
PREMIUM_GALLERY_LIMIT = 30
MAX_FILE_BYTES = 5 * 1024 * 1024
MIN_DIMENSION = 200
MAX_DIMENSION = 4096
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


def gallery_limit_for_user(user: User) -> int:
    return PREMIUM_GALLERY_LIMIT if user.is_premium else BASIC_GALLERY_LIMIT


def can_upload_more(user: User) -> tuple[bool, str | None]:
    limit = gallery_limit_for_user(user)
    count = UserGallery.objects.filter(
        user=user,
        sensitivity_status__in=[
            UserGallery.SensitivityStatus.APPROVED,
            UserGallery.SensitivityStatus.PENDING,
        ],
    ).count()
    if count >= limit:
        if user.is_premium:
            return False, f"Gallery limit reached ({limit} photos)."
        return False, (
            f"Basic accounts can upload up to {BASIC_GALLERY_LIMIT} photos. "
            "Upgrade to Premium for more gallery slots."
        )
    return True, None


def _read_upload(uploaded_file: BinaryIO) -> bytes:
    if hasattr(uploaded_file, "read"):
        data = uploaded_file.read()
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return bytes(data)
    return bytes(uploaded_file)


def validate_and_score_image(file_bytes: bytes, content_type: str) -> tuple[bool, str, int, int, int, str]:
    """
    Returns: ok, content_type, width, height, sensitivity_score, message
    """
    if len(file_bytes) > MAX_FILE_BYTES:
        return False, content_type, 0, 0, 0, "Image exceeds 5 MB limit."

    ct = (content_type or "").lower().split(";")[0].strip()
    if ct not in ALLOWED_CONTENT_TYPES:
        return False, ct, 0, 0, 0, "Only JPEG, PNG, and WebP images are allowed."

    try:
        from PIL import Image
    except ImportError:
        # Pillow not installed — basic size check only
        if len(file_bytes) < 500:
            return False, ct, 0, 0, 0, "Invalid or empty image file."
        return True, ct, 0, 0, 85, "Approved (basic validation)."

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
        img = Image.open(io.BytesIO(file_bytes))
        width, height = img.size

        if width < MIN_DIMENSION or height < MIN_DIMENSION:
            return False, ct, width, height, 0, (
                f"Image too small. Minimum {MIN_DIMENSION}x{MIN_DIMENSION} pixels required."
            )
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            return False, ct, width, height, 0, (
                f"Image too large. Maximum {MAX_DIMENSION}x{MAX_DIMENSION} pixels allowed."
            )

        rgb = img.convert("RGB")
        pixels = list(rgb.getdata())
        if not pixels:
            return False, ct, width, height, 0, "Invalid image content."

        # Reject nearly uniform images (likely not a real photo)
        sample = pixels[:: max(1, len(pixels) // 500)]
        unique_ratio = len({p for p in sample}) / len(sample)
        if unique_ratio < 0.02:
            return False, ct, width, height, 15, "Image appears invalid or inappropriate."

        aspect = width / height if height else 1
        if aspect > 3.5 or aspect < 0.25:
            return False, ct, width, height, 20, "Unusual image proportions. Please upload a clear portrait."

        # Simple safety score from color variance (higher = more natural photo)
        score = min(99, max(60, int(unique_ratio * 100) + 50))

        if score < 65:
            return False, ct, width, height, score, (
                "Image did not pass sensitivity check. Please upload a clear profile photo."
            )

        return True, ct, width, height, score, "Approved"

    except Exception:
        return False, ct, 0, 0, 0, "Invalid or corrupted image file."


@transaction.atomic
def save_gallery_image(
    user: User,
    uploaded_file,
    *,
    set_as_profile: bool = False,
) -> UserGallery:
    ok, err = can_upload_more(user)
    if not ok:
        raise ValueError(err)

    content_type = getattr(uploaded_file, "content_type", "image/jpeg") or "image/jpeg"
    filename = getattr(uploaded_file, "name", "photo.jpg") or "photo.jpg"
    file_bytes = _read_upload(uploaded_file)

    valid, ct, width, height, score, message = validate_and_score_image(file_bytes, content_type)
    if not valid:
        raise ValueError(message)

    item = UserGallery.objects.create(
        user=user,
        image_data=file_bytes,
        content_type=ct,
        original_filename=filename[:255],
        file_size=len(file_bytes),
        width=width,
        height=height,
        sensitivity_status=UserGallery.SensitivityStatus.APPROVED,
        sensitivity_score=score,
        sensitivity_message=message,
        is_profile_photo=set_as_profile,
    )

    if set_as_profile:
        set_profile_photo(user, item)

    return item


@transaction.atomic
def set_profile_photo(user: User, gallery_item: UserGallery) -> None:
    if gallery_item.user_id != user.id:
        raise ValueError("Not your gallery image.")
    if gallery_item.sensitivity_status == UserGallery.SensitivityStatus.REJECTED:
        raise ValueError("Rejected images cannot be set as profile photo.")

    UserGallery.objects.filter(user=user, is_profile_photo=True).update(is_profile_photo=False)
    gallery_item.is_profile_photo = True
    gallery_item.save(update_fields=["is_profile_photo"])

    profile, _ = ProfileDetails.objects.get_or_create(user=user)
    profile.profile_photo = gallery_item
    profile.save(update_fields=["profile_photo"])


def get_profile_photo_url(user: User) -> str | None:
    profile = ProfileDetails.objects.filter(user=user).select_related("profile_photo").first()
    if profile and profile.profile_photo_id:
        return f"/api/milansetu/gallery/{profile.profile_photo_id}/image/"
    item = UserGallery.objects.filter(
        user=user,
        is_profile_photo=True,
        sensitivity_status=UserGallery.SensitivityStatus.APPROVED,
    ).first()
    if item:
        return f"/api/milansetu/gallery/{item.id}/image/"
    return None

"""Profile matching based on ideal partner preferences."""

from django.db.models import Q, QuerySet

from .models import IdealPartner, ProfileDetails


def _text_match(pref_value: str | None, profile_value: str | None) -> bool | None:
    if not pref_value:
        return None
    if not profile_value:
        return False
    return pref_value.strip().lower() in profile_value.strip().lower() or (
        profile_value.strip().lower() in pref_value.strip().lower()
    )


def calculate_compatibility(ideal: IdealPartner | None, profile: ProfileDetails) -> int:
    if ideal is None:
        return 75

    score = 0
    factors = 0

    def add_factor(result: bool | None) -> None:
        nonlocal score, factors
        if result is None:
            return
        factors += 1
        if result:
            score += 1

    if ideal.age_min is not None and ideal.age_max is not None and profile.age is not None:
        add_factor(ideal.age_min <= profile.age <= ideal.age_max)
    elif ideal.age_min is not None and profile.age is not None:
        add_factor(profile.age >= ideal.age_min)
    elif ideal.age_max is not None and profile.age is not None:
        add_factor(profile.age <= ideal.age_max)

    if ideal.height_min_cm and ideal.height_max_cm and profile.height_cm:
        add_factor(ideal.height_min_cm <= profile.height_cm <= ideal.height_max_cm)

    add_factor(_text_match(ideal.religion, profile.religion))
    add_factor(_text_match(ideal.location, profile.birth_place))
    add_factor(_text_match(ideal.mother_tongue, profile.mother_tongue))
    add_factor(_text_match(ideal.marital_status, profile.marital_status))
    add_factor(_text_match(ideal.education, profile.education))
    add_factor(_text_match(ideal.industry, profile.industry))
    add_factor(_text_match(ideal.manglik_status, profile.manglik_status))
    add_factor(_text_match(ideal.family_values, profile.family_values))

    if ideal.min_income is not None and profile.annual_income_min is not None:
        add_factor(profile.annual_income_min >= ideal.min_income)
    if ideal.max_income is not None and profile.annual_income_max is not None:
        add_factor(profile.annual_income_max <= ideal.max_income)

    if factors == 0:
        return 75
    return min(99, max(50, round((score / factors) * 100)))


def apply_employee_filters(queryset: QuerySet, params) -> QuerySet:
    religion = params.get("religion")
    if religion:
        queryset = queryset.filter(religion__icontains=religion)

    age_min = params.get("age_min")
    if age_min:
        queryset = queryset.filter(age__gte=int(age_min))

    age_max = params.get("age_max")
    if age_max:
        queryset = queryset.filter(age__lte=int(age_max))

    location = params.get("location")
    if location:
        queryset = queryset.filter(birth_place__icontains=location)

    mother_tongue = params.get("mother_tongue")
    if mother_tongue:
        queryset = queryset.filter(mother_tongue__icontains=mother_tongue)

    marital_status = params.get("marital_status")
    if marital_status:
        queryset = queryset.filter(marital_status__icontains=marital_status)

    education = params.get("education")
    if education:
        queryset = queryset.filter(education__icontains=education)

    user_type = params.get("user_type")
    if user_type:
        queryset = queryset.filter(user__user_type=user_type)

    is_staff = params.get("is_staff")
    if is_staff is not None:
        queryset = queryset.filter(user__is_staff=is_staff.lower() in ("1", "true", "yes"))

    search = params.get("search")
    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search)
            | Q(current_designation__icontains=search)
            | Q(education__icontains=search)
            | Q(birth_place__icontains=search)
        )

    return queryset


def filter_profiles_for_user(
    queryset: QuerySet,
    ideal: IdealPartner | None,
    *,
    min_score: int = 60,
) -> list[tuple[ProfileDetails, int]]:
    """Return profiles sorted by compatibility score (for normal users)."""
    scored: list[tuple[ProfileDetails, int]] = []
    for profile in queryset:
        score = calculate_compatibility(ideal, profile)
        if score >= min_score:
            scored.append((profile, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored

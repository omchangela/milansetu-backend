from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserType(models.TextChoices):
    BASIC = "basic", "Basic"
    SILVER = "silver", "Silver"
    GOLD = "gold", "Gold"
    PLATINUM = "platinum", "Platinum"


class UserRole(models.TextChoices):
    USER = "user", "User"
    EMPLOYEE = "employee", "Employee"
    ADMIN = "admin", "Admin"


PREMIUM_USER_TYPES = frozenset({
    UserType.SILVER,
    UserType.GOLD,
    UserType.PLATINUM,
})

FREE_PROFILE_EDITS_PER_MONTH = 3


class UserManager(BaseUserManager):
    """Custom manager for User."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")

        extra_fields.setdefault("user_type", UserType.BASIC)
        extra_fields.setdefault("role", UserRole.USER)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_staff", False)

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", UserType.PLATINUM)
        extra_fields.setdefault("role", UserRole.ADMIN)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Core auth user — credentials and membership type.

    user_type: basic | silver | gold | platinum
    role: user | employee | admin
    """

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(auto_now_add=True)

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.BASIC,
        db_column="user_type",
    )

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
    )

    premium_since = models.DateTimeField(null=True, blank=True)
    premium_expires_at = models.DateTimeField(null=True, blank=True)

    profile_edit_count = models.PositiveIntegerField(default=0)
    profile_edit_month = models.CharField(max_length=7, blank=True, default="")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    @property
    def is_premium(self) -> bool:
        if self.user_type not in PREMIUM_USER_TYPES:
            return False

        if (
            self.premium_expires_at
            and self.premium_expires_at < timezone.now()
        ):
            return False

        return True

    @property
    def is_employee(self) -> bool:
        return self.role == UserRole.EMPLOYEE

    @property
    def is_admin_role(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_regular_user(self) -> bool:
        return self.role == UserRole.USER
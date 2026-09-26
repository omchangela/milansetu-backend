from django.db import migrations, models


def forwards_user_type(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.all():
        if user.is_superuser:
            user.user_type = "platinum"
            user.is_staff = True
        elif getattr(user, "role", None) == "admin":
            user.user_type = "platinum"
            user.is_staff = True
        elif getattr(user, "role", None) == "employee":
            user.user_type = "gold"
            user.is_staff = True
        elif getattr(user, "membership_tier", None) == "premium":
            user.user_type = "gold"
        else:
            user.user_type = "basic"
        user.save(update_fields=["user_type", "is_staff"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_user_membership_tier_user_premium_expires_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="user_type",
            field=models.CharField(
                choices=[
                    ("basic", "Basic"),
                    ("silver", "Silver"),
                    ("gold", "Gold"),
                    ("platinum", "Platinum"),
                ],
                default="basic",
                max_length=20,
            ),
        ),
        migrations.RunPython(forwards_user_type, migrations.RunPython.noop),
        migrations.RemoveField(model_name="user", name="role"),
        migrations.RemoveField(model_name="user", name="membership_tier"),
    ]

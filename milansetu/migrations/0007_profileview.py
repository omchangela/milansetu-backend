import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('milansetu', '0006_fcm_token'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('viewed_at', models.DateTimeField(auto_now_add=True)),
                ('viewer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile_views_made',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('viewed_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile_views_received',
                    to='milansetu.profiledetails',
                )),
            ],
            options={
                'db_table': 'profile_views',
                'ordering': ['-viewed_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='profileview',
            constraint=models.UniqueConstraint(
                fields=['viewer', 'viewed_profile'],
                name='unique_profile_view',
            ),
        ),
    ]

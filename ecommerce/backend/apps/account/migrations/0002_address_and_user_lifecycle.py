import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="lock_reason",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="user",
            name="locked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="Address",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("recipient_name", models.CharField(max_length=255)),
                (
                    "phone",
                    models.CharField(
                        max_length=20,
                        validators=[
                            django.core.validators.RegexValidator(
                                message=(
                                    "Số điện thoại phải gồm 9-15 chữ số và có thể bắt đầu "
                                    "bằng dấu +"
                                ),
                                regex="^\\+?[0-9]{9,15}$",
                            ),
                        ],
                    ),
                ),
                ("province", models.CharField(max_length=100)),
                ("district", models.CharField(max_length=100)),
                ("ward", models.CharField(max_length=100)),
                ("detail_address", models.CharField(max_length=500)),
                ("is_default", models.BooleanField(default=False)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="addresses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-is_default", "-updated_at"),
                "indexes": [
                    models.Index(
                        fields=["user", "is_deleted"],
                        name="acct_addr_user_active_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(is_default=True, is_deleted=False),
                        fields=("user",),
                        name="account_address_one_active_default",
                    ),
                ],
            },
        ),
    ]

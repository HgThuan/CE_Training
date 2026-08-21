import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0005_chat_support_operations"),
        ("product", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendationProfile",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("category_weights", models.JSONField(blank=True, default=dict)),
                ("brand_weights", models.JSONField(blank=True, default=dict)),
                ("related_product_ids", models.JSONField(blank=True, default=list)),
                ("model_name", models.CharField(default="purchase-cooccurrence-v1", max_length=80)),
                ("generated_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="recommendation_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "ai_recommendation_profiles",
                "ordering": ("-generated_at", "-id"),
            },
        ),
        migrations.CreateModel(
            name="RecommendationEvent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("recommendation_id", models.UUIDField(db_index=True)),
                ("visitor_id_hash", models.CharField(blank=True, db_index=True, max_length=64)),
                ("event_type", models.CharField(choices=[("impression", "Impression"), ("click", "Click"), ("add_to_cart", "Add to cart"), ("purchase", "Purchase")], db_index=True, max_length=20)),
                ("source", models.CharField(choices=[("home", "Home"), ("product", "Product recommendation"), ("similar", "Similar products"), ("search", "AI search")], db_index=True, max_length=20)),
                ("position", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("context", models.JSONField(blank=True, default=dict)),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recommendation_events", to="product.product")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recommendation_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "ai_recommendation_events",
                "ordering": ("-created_at", "-id"),
                "indexes": [
                    models.Index(fields=["event_type", "-created_at"], name="ai_rec_event_type_idx"),
                    models.Index(fields=["user", "product", "-created_at"], name="ai_rec_user_product_idx"),
                ],
            },
        ),
    ]

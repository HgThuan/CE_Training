from django.conf import settings
from django.db import migrations


def preserve_existing_shop_image_urls(apps, schema_editor):
    shop_model = apps.get_model("account", "Shop")
    media_url = settings.MEDIA_URL.rstrip("/")

    for shop in shop_model.objects.only(
        "id",
        "logo",
        "cover",
        "logo_url",
        "cover_url",
    ).iterator():
        update_fields = []
        for image_field, url_field in (("logo", "logo_url"), ("cover", "cover_url")):
            image_name = str(getattr(shop, image_field) or "")
            if image_name and not getattr(shop, url_field):
                prefix = media_url if media_url else ""
                setattr(shop, url_field, f"{prefix}/{image_name.lstrip('/')}")
                update_fields.append(url_field)
        if update_fields:
            shop.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0004_shop_cover_shop_logo"),
    ]

    operations = [
        migrations.RunPython(
            preserve_existing_shop_image_urls,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="shop",
            name="cover",
        ),
        migrations.RemoveField(
            model_name="shop",
            name="logo",
        ),
    ]

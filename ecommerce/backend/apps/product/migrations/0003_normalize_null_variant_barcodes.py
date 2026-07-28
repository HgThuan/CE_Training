from django.db import migrations


def normalize_null_variant_barcodes(apps, schema_editor):
    product_variant = apps.get_model("product", "ProductVariant")
    product_variant.objects.filter(barcode="None").update(barcode=None)


class Migration(migrations.Migration):
    dependencies = [
        ("product", "0002_productvariant_stock_quantity"),
    ]

    operations = [
        migrations.RunPython(
            normalize_null_variant_barcodes,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

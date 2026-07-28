from django.core.management.base import BaseCommand
from django.db import transaction

from apps.inventory.models import InventoryBalance
from apps.product.models import ProductVariant


class Command(BaseCommand):
    help = "Create missing InventoryBalance rows from deprecated ProductVariant.stock_quantity."

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        variants = ProductVariant.objects.order_by("pk").iterator(chunk_size=500)
        for variant in variants:
            _, created = InventoryBalance.objects.get_or_create(
                variant=variant,
                defaults={
                    "available_stock": variant.stock_quantity,
                    "reserved_stock": 0,
                },
            )
            created_count += int(created)

        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} missing inventory balance(s).")
        )

from django.core.management.base import BaseCommand

from apps.inventory.models import StockEntry
from apps.inventory.services import StockService
from apps.product.models import ProductVariant


class Command(BaseCommand):
    help = "Create one confirmed demo receipt per shop that has product variants."

    def add_arguments(self, parser):
        parser.add_argument("--quantity", type=int, default=20)
        parser.add_argument("--unit-cost", type=int, default=50000)

    def handle(self, *args, **options):
        quantity = options["quantity"]
        unit_cost = options["unit_cost"]
        if quantity <= 0 or unit_cost < 0:
            self.stderr.write("quantity must be positive and unit-cost must be non-negative")
            return

        seeded_shops = 0
        shop_ids = (
            ProductVariant.objects.filter(is_deleted=False, product__is_deleted=False)
            .order_by("shop_id")
            .values_list("shop_id", flat=True)
            .distinct()
        )
        for shop_id in shop_ids:
            variants = list(
                ProductVariant.objects.select_related("shop__owner")
                .filter(
                    shop_id=shop_id,
                    is_deleted=False,
                    product__is_deleted=False,
                )
                .order_by("created_at")[:5]
            )
            if not variants:
                continue
            marker = "seed_inventory_demo"
            if StockEntry.objects.filter(shop_id=shop_id, note=marker).exists():
                continue
            owner = variants[0].shop.owner
            entry = StockService.create_stock_entry(
                user=owner,
                data={
                    "supplier_name": "Nhà cung cấp Demo",
                    "note": marker,
                    "items": [
                        {
                            "variant_id": variant.pk,
                            "quantity": quantity,
                            "unit_cost": unit_cost,
                        }
                        for variant in variants
                    ],
                },
            )
            StockService.confirm_stock_entry(entry.pk, owner)
            seeded_shops += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded inventory for {seeded_shops} shop(s).")
        )


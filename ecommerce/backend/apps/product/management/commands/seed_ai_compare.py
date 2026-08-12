from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.account.models import SellerProfile, Shop, User
from apps.catalog.models import Brand, Category
from apps.inventory.models import InventoryBalance
from apps.product.models import (
    Attribute,
    AttributeValue,
    Product,
    ProductAttributeValue,
    ProductMedia,
    ProductVariant,
)

SMARTPHONE_ATTRIBUTES = [
    {"code": "cpu", "name": "Vi xử lý (CPU)"},
    {"code": "ram", "name": "Dung lượng RAM"},
    {"code": "rom", "name": "Bộ nhớ trong (ROM)"},
    {"code": "camera", "name": "Camera chính"},
    {"code": "battery", "name": "Dung lượng pin"},
    {"code": "screen", "name": "Kích thước màn hình"},
]

COMPARE_PRODUCTS = [
    {
        "name": "Điện thoại Apple iPhone 15 Pro",
        "slug": "dien-thoai-apple-iphone-15-pro-compare",
        "category": ("Điện thoại", "dien-thoai"),
        "brand": ("Apple", "apple"),
        "description": "iPhone 15 Pro với khung titanium siêu nhẹ, chip A17 Pro mạnh mẽ, và cụm camera chuyên nghiệp 48MP.",
        "image": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.8",
        "rating_count": 150,
        "sold_count": 500,
        "variants": (("256GB", 28990000, 27990000), ("512GB", 34990000, 33990000)),
        "attributes": {
            "cpu": "Apple A17 Pro",
            "ram": "8GB",
            "rom": "256GB / 512GB",
            "camera": "48MP + 12MP + 12MP",
            "battery": "3274 mAh",
            "screen": "6.1 inch, Super Retina XDR OLED, 120Hz",
        }
    },
    {
        "name": "Điện thoại Apple iPhone 15 Pro Max",
        "slug": "dien-thoai-apple-iphone-15-pro-max-compare",
        "category": ("Điện thoại", "dien-thoai"),
        "brand": ("Apple", "apple"),
        "description": "iPhone 15 Pro Max với màn hình lớn, pin trâu, khung titanium siêu bền và camera zoom quang học 5x.",
        "image": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.9",
        "rating_count": 220,
        "sold_count": 800,
        "variants": (("256GB", 34990000, 32990000), ("512GB", 40990000, 38990000)),
        "attributes": {
            "cpu": "Apple A17 Pro",
            "ram": "8GB",
            "rom": "256GB / 512GB",
            "camera": "48MP + 12MP + 12MP (Zoom 5x)",
            "battery": "4422 mAh",
            "screen": "6.7 inch, Super Retina XDR OLED, 120Hz",
        }
    },
    {
        "name": "Điện thoại Samsung Galaxy S24 Ultra",
        "slug": "dien-thoai-samsung-galaxy-s24-ultra-compare",
        "category": ("Điện thoại", "dien-thoai"),
        "brand": ("Samsung", "samsung"),
        "description": "Galaxy S24 Ultra với AI thông minh, bút S-Pen tích hợp, khung titanium và camera 200MP siêu zoom.",
        "image": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.85",
        "rating_count": 180,
        "sold_count": 650,
        "variants": (("256GB", 33990000, 29990000), ("512GB", 37990000, 34990000)),
        "attributes": {
            "cpu": "Snapdragon 8 Gen 3 for Galaxy",
            "ram": "12GB",
            "rom": "256GB / 512GB",
            "camera": "200MP + 50MP + 12MP + 10MP",
            "battery": "5000 mAh",
            "screen": "6.8 inch, Dynamic AMOLED 2X, 120Hz",
        }
    },
    {
        "name": "Điện thoại Google Pixel 8 Pro",
        "slug": "dien-thoai-google-pixel-8-pro-compare",
        "category": ("Điện thoại", "dien-thoai"),
        "brand": ("Google", "google"),
        "description": "Google Pixel 8 Pro với camera AI nhiếp ảnh điện toán xuất sắc, màn hình Super Actua siêu sáng và Android thuần.",
        "image": "https://images.unsplash.com/photo-1598327105666-5b89351cb31b?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.7",
        "rating_count": 90,
        "sold_count": 300,
        "variants": (("128GB", 25990000, 24500000), ("256GB", 27990000, 26500000)),
        "attributes": {
            "cpu": "Google Tensor G3",
            "ram": "12GB",
            "rom": "128GB / 256GB",
            "camera": "50MP + 48MP + 48MP",
            "battery": "5050 mAh",
            "screen": "6.7 inch, LTPO OLED, 120Hz",
        }
    },
    {
        "name": "Điện thoại Xiaomi 14 Ultra",
        "slug": "dien-thoai-xiaomi-14-ultra-compare",
        "category": ("Điện thoại", "dien-thoai"),
        "brand": ("Xiaomi", "xiaomi"),
        "description": "Thiết kế cao cấp, hệ thống camera Leica đỉnh cao chuyên nhiếp ảnh và sạc siêu tốc.",
        "image": "https://images.unsplash.com/photo-1598327105666-5b89351cb31b?auto=format&fit=crop&w=1200&q=80", # Using placeholder
        "rating": "4.75",
        "rating_count": 110,
        "sold_count": 420,
        "variants": (("512GB", 32990000, 29990000),),
        "attributes": {
            "cpu": "Snapdragon 8 Gen 3",
            "ram": "16GB",
            "rom": "512GB",
            "camera": "50MP (Leica) + 50MP + 50MP + 50MP",
            "battery": "5300 mAh",
            "screen": "6.73 inch, LTPO AMOLED, 120Hz",
        }
    },
]

class Command(BaseCommand):
    help = "Seed specific smartphone products with detailed attributes for testing AI Product Comparison."

    @transaction.atomic
    def handle(self, *args, **options):
        shop = self._get_shop()
        created_products = 0

        # Create global attributes if not exists
        attr_objs = {}
        for attr in SMARTPHONE_ATTRIBUTES:
            obj, _ = Attribute.objects.get_or_create(
                code=attr["code"],
                shop__isnull=True, # Global attribute
                defaults={
                    "name": attr["name"],
                    "display_type": Attribute.DisplayType.TEXT,
                }
            )
            attr_objs[attr["code"]] = obj

        for data in COMPARE_PRODUCTS:
            category = self._get_category(*data["category"])
            brand = self._get_brand(*data["brand"])
            prices = [Decimal(str(variant[2])) for variant in data["variants"]]
            
            product, created = Product.objects.update_or_create(
                shop=shop,
                slug=data["slug"],
                defaults={
                    "category": category,
                    "brand": brand,
                    "name": data["name"],
                    "short_description": data["description"],
                    "description": f"<p>{data['description']}</p>",
                    "status": Product.Status.APPROVED,
                    "approved_at": timezone.now(),
                    "rating_average": Decimal(data["rating"]),
                    "rating_count": data["rating_count"],
                    "sold_count": data["sold_count"],
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "is_deleted": False,
                    "deleted_at": None,
                },
            )
            if created:
                created_products += 1

            # Seed Media
            ProductMedia.objects.update_or_create(
                product=product,
                is_primary=True,
                defaults={
                    "media_type": ProductMedia.MediaType.IMAGE,
                    "file_url": data["image"],
                    "thumbnail_url": data["image"],
                    "alt_text": data["name"],
                    "sort_order": 0,
                },
            )

            # Seed Attributes
            for attr_code, attr_val_str in data.get("attributes", {}).items():
                attr_obj = attr_objs[attr_code]
                attr_val, _ = AttributeValue.objects.get_or_create(
                    attribute=attr_obj,
                    value=attr_val_str[:120], # max_length=120
                    defaults={
                        "display_value": attr_val_str[:120],
                    }
                )
                ProductAttributeValue.objects.update_or_create(
                    product=product,
                    attribute_value=attr_val
                )

            # Seed Variants
            stock = 100
            for variant_number, (variant_name, original_price, sale_price) in enumerate(
                data["variants"], start=1
            ):
                sku = f"AI-COMPARE-{product.id.hex[:6].upper()}-{variant_number:02d}"
                variant, _ = ProductVariant.objects.update_or_create(
                    shop=shop,
                    sku=sku,
                    defaults={
                        "product": product,
                        "name": variant_name,
                        "original_price": Decimal(str(original_price)),
                        "sale_price": Decimal(str(sale_price)),
                        "cost_price": Decimal(str(sale_price)) * Decimal("0.7"),
                        "stock_quantity": stock,
                        "weight_grams": 500,
                        "is_active": True,
                        "is_deleted": False,
                        "deleted_at": None,
                    },
                )
                InventoryBalance.objects.get_or_create(
                    variant=variant,
                    defaults={
                        "available_stock": stock,
                        "reserved_stock": 0,
                        "low_stock_threshold": 5,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {len(COMPARE_PRODUCTS)} compare products for shop '{shop.name}'."
            )
        )

    @staticmethod
    def _get_shop() -> Shop:
        owner, _ = User.objects.get_or_create(
            email="seed-products@example.com",
            defaults={
                "role": User.Role.SELLER,
                "full_name": "Nguyễn Minh Demo",
                "is_active": True,
                "is_email_verified": True,
            },
        )
        SellerProfile.objects.update_or_create(
            user=owner,
            defaults={
                "business_name": "Tech Demo Store",
                "business_address": "Quận 1, TP. Hồ Chí Minh",
                "contact_phone": "0901234567",
                "onboarding_status": SellerProfile.OnboardingStatus.APPROVED,
                "verification_status": SellerProfile.VerificationStatus.VERIFIED,
                "is_deleted": False,
                "deleted_at": None,
            },
        )
        shop, _ = Shop.objects.update_or_create(
            owner=owner,
            defaults={
                "name": "Tech Demo Store",
                "slug": "tech-demo-store",
                "description": "Gian hàng công nghệ chính hãng dành cho dữ liệu demo.",
                "status": Shop.Status.APPROVED,
                "average_rating": Decimal("4.82"),
                "is_deleted": False,
                "deleted_at": None,
            },
        )
        return shop

    @staticmethod
    def _get_category(name: str, slug: str) -> Category:
        category, _ = Category.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "is_active": True,
                "is_deleted": False,
                "deleted_at": None,
            },
        )
        return category

    @staticmethod
    def _get_brand(name: str, slug: str) -> Brand:
        brand, _ = Brand.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": f"Sản phẩm chính hãng {name}.",
                "is_active": True,
                "is_deleted": False,
                "deleted_at": None,
            },
        )
        return brand

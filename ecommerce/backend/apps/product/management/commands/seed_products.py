from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.account.models import SellerProfile, Shop, User
from apps.catalog.models import Brand, Category
from apps.inventory.models import InventoryBalance
from apps.product.models import Product, ProductMedia, ProductVariant

PRODUCTS = (
    {
        "name": "Điện thoại Galaxy S24 Ultra 5G",
        "slug": "dien-thoai-galaxy-s24-ultra-5g",
        "category": ("Điện thoại", "dien-thoai"),
        "brand": ("Samsung", "samsung"),
        "description": "Điện thoại cao cấp với bút S Pen, camera sắc nét và hiệu năng mạnh mẽ.",
        "image": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.85",
        "rating_count": 186,
        "sold_count": 524,
        "variants": (("256GB", 33990000, 29990000), ("512GB", 37990000, 34990000)),
    },
    {
        "name": "Điện thoại iPhone 15 Pro Max",
        "slug": "dien-thoai-iphone-15-pro-max",
        "category": ("Điện thoại", "dien-thoai"),
        "brand": ("Apple", "apple"),
        "description": "Thiết kế titan, chip hiệu năng cao và hệ thống camera chuyên nghiệp.",
        "image": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.92",
        "rating_count": 241,
        "sold_count": 731,
        "variants": (("256GB", 34990000, 31990000), ("512GB", 40990000, 37990000)),
    },
    {
        "name": "Laptop MacBook Air M3 13 inch",
        "slug": "laptop-macbook-air-m3-13-inch",
        "category": ("Laptop", "laptop"),
        "brand": ("Apple", "apple"),
        "description": "Laptop mỏng nhẹ, pin lâu, phù hợp học tập và công việc sáng tạo.",
        "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.88",
        "rating_count": 119,
        "sold_count": 302,
        "variants": (("8GB/256GB", 27990000, 26490000), ("16GB/512GB", 36990000, 34990000)),
    },
    {
        "name": "Laptop Dell XPS 13 Plus",
        "slug": "laptop-dell-xps-13-plus",
        "category": ("Laptop", "laptop"),
        "brand": ("Dell", "dell"),
        "description": (
            "Màn hình sắc nét, thiết kế tối giản và hiệu năng ổn định cho dân văn phòng."
        ),
        "image": "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.74",
        "rating_count": 78,
        "sold_count": 196,
        "variants": (("i5/16GB/512GB", 28990000, 25990000), ("i7/16GB/1TB", 35990000, 32990000)),
    },
    {
        "name": "Tai nghe Sony WH-1000XM5",
        "slug": "tai-nghe-sony-wh-1000xm5",
        "category": ("Âm thanh", "am-thanh"),
        "brand": ("Sony", "sony"),
        "description": "Tai nghe không dây chống ồn chủ động, âm thanh chi tiết và đeo thoải mái.",
        "image": "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.81",
        "rating_count": 163,
        "sold_count": 448,
        "variants": (("Đen", 8990000, 7490000), ("Bạc", 8990000, 7690000)),
    },
    {
        "name": "Tai nghe AirPods Pro thế hệ 2",
        "slug": "tai-nghe-airpods-pro-the-he-2",
        "category": ("Âm thanh", "am-thanh"),
        "brand": ("Apple", "apple"),
        "description": "Chống ồn chủ động, âm thanh thích ứng và hộp sạc USB-C tiện lợi.",
        "image": "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.89",
        "rating_count": 207,
        "sold_count": 826,
        "variants": (("Trắng", 6990000, 5990000),),
    },
    {
        "name": "Đồng hồ Apple Watch Series 9",
        "slug": "dong-ho-apple-watch-series-9",
        "category": ("Thiết bị đeo", "thiet-bi-deo"),
        "brand": ("Apple", "apple"),
        "description": "Theo dõi sức khỏe, luyện tập và nhận thông báo ngay trên cổ tay.",
        "image": "https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.76",
        "rating_count": 94,
        "sold_count": 251,
        "variants": (("41mm", 10990000, 9490000), ("45mm", 11990000, 10490000)),
    },
    {
        "name": "Đồng hồ Samsung Galaxy Watch6",
        "slug": "dong-ho-samsung-galaxy-watch6",
        "category": ("Thiết bị đeo", "thiet-bi-deo"),
        "brand": ("Samsung", "samsung"),
        "description": (
            "Đồng hồ thông minh thanh lịch với các tính năng theo dõi sức khỏe toàn diện."
        ),
        "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.68",
        "rating_count": 71,
        "sold_count": 184,
        "variants": (("40mm", 6990000, 5490000), ("44mm", 7490000, 5990000)),
    },
    {
        "name": "Loa Bluetooth JBL Charge 5",
        "slug": "loa-bluetooth-jbl-charge-5",
        "category": ("Âm thanh", "am-thanh"),
        "brand": ("JBL", "jbl"),
        "description": "Loa di động chống nước, âm bass mạnh và thời lượng pin lên đến 20 giờ.",
        "image": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.72",
        "rating_count": 132,
        "sold_count": 479,
        "variants": (("Đen", 3990000, 3290000), ("Xanh", 3990000, 3390000)),
    },
    {
        "name": "Máy tính bảng iPad Air M2",
        "slug": "may-tinh-bang-ipad-air-m2",
        "category": ("Máy tính bảng", "may-tinh-bang"),
        "brand": ("Apple", "apple"),
        "description": "Màn hình Liquid Retina, chip M2 mạnh mẽ cho học tập, làm việc và giải trí.",
        "image": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.84",
        "rating_count": 106,
        "sold_count": 267,
        "variants": (("128GB Wi-Fi", 16990000, 15990000), ("256GB Wi-Fi", 19990000, 18990000)),
    },
    {
        "name": "Bàn phím cơ Keychron K2 Pro",
        "slug": "ban-phim-co-keychron-k2-pro",
        "category": ("Phụ kiện", "phu-kien"),
        "brand": ("Keychron", "keychron"),
        "description": "Bàn phím cơ không dây layout 75%, hỗ trợ nhiều hệ điều hành.",
        "image": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.70",
        "rating_count": 88,
        "sold_count": 329,
        "variants": (("Red Switch", 2990000, 2590000), ("Brown Switch", 2990000, 2690000)),
    },
    {
        "name": "Chuột không dây Logitech MX Master 3S",
        "slug": "chuot-khong-day-logitech-mx-master-3s",
        "category": ("Phụ kiện", "phu-kien"),
        "brand": ("Logitech", "logitech"),
        "description": "Chuột công thái học cao cấp, cuộn siêu nhanh và kết nối đa thiết bị.",
        "image": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.79",
        "rating_count": 142,
        "sold_count": 511,
        "variants": (("Graphite", 2790000, 2390000), ("Pale Gray", 2790000, 2490000)),
    },
)


class Command(BaseCommand):
    help = "Seed approved demo products with variants, images, and inventory."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=len(PRODUCTS),
            help=f"Number of products to seed (1-{len(PRODUCTS)}).",
        )
        parser.add_argument(
            "--stock",
            type=int,
            default=50,
            help="Initial stock for newly-created variants.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        stock = options["stock"]
        if not 1 <= count <= len(PRODUCTS):
            raise CommandError(f"count must be between 1 and {len(PRODUCTS)}")
        if stock < 0:
            raise CommandError("stock must be non-negative")

        shop = self._get_shop()
        created_products = 0
        created_variants = 0

        for product_number, data in enumerate(PRODUCTS[:count], start=1):
            category = self._get_category(*data["category"])
            brand = self._get_brand(*data["brand"])
            prices = [Decimal(str(variant[2])) for variant in data["variants"]]
            product, product_created = Product.objects.update_or_create(
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
            created_products += int(product_created)

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

            for variant_number, (variant_name, original_price, sale_price) in enumerate(
                data["variants"], start=1
            ):
                sku = f"DEMO-{product_number:02d}-{variant_number:02d}"
                variant, variant_created = ProductVariant.objects.update_or_create(
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
                created_variants += int(variant_created)
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
                f"Seeded {count} products for '{shop.name}' "
                f"({created_products} products and {created_variants} variants created)."
            )
        )

    @staticmethod
    def _get_shop() -> Shop:
        owner, owner_created = User.objects.get_or_create(
            email="seed-products@example.com",
            defaults={
                "role": User.Role.SELLER,
                "full_name": "Nguyễn Minh Demo",
                "is_active": True,
                "is_email_verified": True,
            },
        )
        user_updates = []
        if owner_created or not owner.password:
            owner.set_unusable_password()
            user_updates.append("password")
        if owner.role != User.Role.SELLER:
            owner.role = User.Role.SELLER
            user_updates.append("role")
        if not owner.is_active:
            owner.is_active = True
            user_updates.append("is_active")
        if not owner.is_email_verified:
            owner.is_email_verified = True
            user_updates.append("is_email_verified")
        if user_updates:
            owner.save(update_fields=[*user_updates, "updated_at"])

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

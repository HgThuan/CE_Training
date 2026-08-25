from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone
from django.utils.text import slugify

from apps.account.models import CustomerProfile, SellerProfile, Shop, User
from apps.catalog.models import Brand, Category
from apps.inventory.models import InventoryBalance
from apps.order.models import Order, OrderItem, ShopOrder
from apps.product.models import (
    Attribute,
    AttributeValue,
    Product,
    ProductAttributeValue,
    ProductMedia,
    ProductVariant,
)
from apps.review.models import Review

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

PRODUCTS += (
    {
        "name": "Điện thoại Samsung Galaxy A55 5G",
        "slug": "dien-thoai-samsung-galaxy-a55-5g",
        "category": ("Điện thoại", "dien-thoai"),
        "brand": ("Samsung", "samsung"),
        "description": (
            "Điện thoại tầm trung có màn hình AMOLED 120Hz, camera chống rung quang học "
            "và khung kim loại chắc chắn. Pin 5.000 mAh phù hợp học tập, mạng xã hội và "
            "quay video hằng ngày; máy hỗ trợ kháng nước IP67 và cập nhật phần mềm dài hạn."
        ),
        "image": "https://images.unsplash.com/photo-1616348436168-de43ad0db179?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.68",
        "rating_count": 154,
        "sold_count": 462,
        "variants": (("8GB/128GB", 10990000, 9490000), ("8GB/256GB", 11990000, 10490000)),
        "attributes": {
            "Phân khúc": "Tầm trung",
            "Màn hình": "6.6 inch AMOLED 120Hz",
            "Camera": "50MP chống rung OIS",
            "Pin": "5.000 mAh",
            "Chống nước": "IP67",
            "Nhu cầu": "Học tập, mạng xã hội, quay video",
            "Bảo hành": "12 tháng",
        },
        "review_strength": "màn hình mượt, pin bền và camera chụp ban ngày rõ nét",
        "review_caveat": "máy hơi nặng khi dùng bằng một tay lâu",
    },
    {
        "name": "Điện thoại Xiaomi Redmi Note 13 Pro 5G",
        "slug": "dien-thoai-xiaomi-redmi-note-13-pro-5g",
        "category": ("Điện thoại", "dien-thoai"),
        "brand": ("Xiaomi", "xiaomi"),
        "description": (
            "Điện thoại giá tốt nổi bật với camera 200MP, màn hình AMOLED 120Hz và sạc nhanh "
            "67W. Cấu hình phù hợp chơi game phổ thông, xem phim và chụp ảnh độ phân giải cao; "
            "đây là lựa chọn đáng cân nhắc cho ngân sách dưới 10 triệu đồng."
        ),
        "image": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.61",
        "rating_count": 203,
        "sold_count": 688,
        "variants": (("8GB/256GB", 9490000, 7990000), ("12GB/512GB", 10990000, 9290000)),
        "attributes": {
            "Phân khúc": "Cận trung cấp",
            "Màn hình": "6.67 inch AMOLED 120Hz",
            "Camera": "200MP chống rung OIS",
            "Pin": "5.100 mAh, sạc nhanh 67W",
            "Nhu cầu": "Chơi game phổ thông, chụp ảnh, xem phim",
            "Bảo hành": "18 tháng",
        },
        "review_strength": "camera nhiều chi tiết, sạc nhanh và hiệu năng tốt trong tầm giá",
        "review_caveat": "giao diện có khá nhiều ứng dụng cài sẵn",
    },
    {
        "name": "Điện thoại Google Pixel 8a",
        "slug": "dien-thoai-google-pixel-8a",
        "category": ("Điện thoại", "dien-thoai"),
        "brand": ("Google", "google"),
        "description": (
            "Điện thoại Android nhỏ gọn chú trọng nhiếp ảnh điện toán, ảnh chân dung và chụp "
            "đêm. Pixel 8a có màn hình OLED 120Hz, nhiều tính năng AI chỉnh ảnh và bảy năm cập "
            "nhật; phù hợp người muốn trải nghiệm Android thuần và camera dễ dùng."
        ),
        "image": "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.73",
        "rating_count": 87,
        "sold_count": 174,
        "variants": (("128GB Đen", 14990000, 13490000), ("256GB Xanh", 16990000, 15490000)),
        "attributes": {
            "Phân khúc": "Cao cấp nhỏ gọn",
            "Màn hình": "6.1 inch OLED 120Hz",
            "Camera": "64MP, AI chỉnh ảnh, chụp đêm",
            "Pin": "4.492 mAh",
            "Nhu cầu": "Chụp chân dung, Android thuần, máy nhỏ gọn",
            "Bảo hành": "12 tháng tại cửa hàng",
        },
        "review_strength": "camera chụp người tự nhiên và phần mềm gọn gàng",
        "review_caveat": "tốc độ sạc chậm hơn nhiều máy Android cùng giá",
    },
    {
        "name": "Laptop Lenovo Yoga Slim 7 14IMH9",
        "slug": "laptop-lenovo-yoga-slim-7-14imh9",
        "category": ("Laptop", "laptop"),
        "brand": ("Lenovo", "lenovo"),
        "description": (
            "Ultrabook vỏ nhôm nhẹ với màn hình OLED 14 inch, bàn phím êm và thời lượng pin đủ "
            "một ngày làm việc. Cấu hình Intel Core Ultra hỗ trợ các tác vụ AI, họp trực tuyến, "
            "lập trình và chỉnh ảnh nhẹ; thích hợp người thường xuyên di chuyển."
        ),
        "image": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.77",
        "rating_count": 64,
        "sold_count": 121,
        "variants": (
            ("Core Ultra 5/16GB/512GB", 24990000, 22990000),
            ("Core Ultra 7/32GB/1TB", 32990000, 30490000),
        ),
        "attributes": {
            "Phân khúc": "Ultrabook",
            "Màn hình": "14 inch OLED 2.8K",
            "Trọng lượng": "1,39 kg",
            "Pin": "Khoảng 12 giờ sử dụng hỗn hợp",
            "Nhu cầu": "Văn phòng, lập trình, chỉnh ảnh, di chuyển",
            "Bảo hành": "24 tháng",
        },
        "review_strength": "màn hình đẹp, bàn phím tốt và thân máy nhẹ",
        "review_caveat": "không phù hợp chơi game nặng vì dùng đồ họa tích hợp",
    },
    {
        "name": "Laptop ASUS ROG Zephyrus G14",
        "slug": "laptop-asus-rog-zephyrus-g14",
        "category": ("Laptop", "laptop"),
        "brand": ("ASUS", "asus"),
        "description": (
            "Laptop gaming 14 inch cân bằng giữa hiệu năng mạnh và tính di động. Màn hình OLED "
            "120Hz hiển thị màu chính xác, GPU rời đáp ứng game AAA, dựng video và đồ họa 3D; "
            "hệ thống tản nhiệt được tối ưu cho thân máy mỏng."
        ),
        "image": "https://images.unsplash.com/photo-1603302576837-37561b2e2302?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.82",
        "rating_count": 92,
        "sold_count": 147,
        "variants": (
            ("Ryzen 9/16GB/1TB/RTX 4060", 48990000, 45490000),
            ("Ryzen 9/32GB/1TB/RTX 4070", 59990000, 55990000),
        ),
        "attributes": {
            "Phân khúc": "Gaming cao cấp",
            "Màn hình": "14 inch OLED 3K 120Hz",
            "Đồ họa": "NVIDIA GeForce RTX 4060 hoặc RTX 4070",
            "Trọng lượng": "1,5 kg",
            "Nhu cầu": "Game AAA, dựng video, đồ họa 3D",
            "Bảo hành": "24 tháng",
        },
        "review_strength": "hiệu năng mạnh trong thân máy nhỏ và màn hình OLED rất đẹp",
        "review_caveat": "quạt nghe rõ khi chạy game nặng và giá khá cao",
    },
    {
        "name": "Laptop Acer Aspire 5 A515",
        "slug": "laptop-acer-aspire-5-a515",
        "category": ("Laptop", "laptop"),
        "brand": ("Acer", "acer"),
        "description": (
            "Laptop phổ thông dành cho sinh viên và nhân viên văn phòng, có đầy đủ cổng kết nối "
            "và khả năng nâng cấp bộ nhớ. Máy xử lý tốt tài liệu, học trực tuyến, duyệt web nhiều "
            "tab và các tác vụ lập trình cơ bản với ngân sách hợp lý."
        ),
        "image": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.55",
        "rating_count": 118,
        "sold_count": 355,
        "variants": (
            ("Core i5/8GB/512GB", 15990000, 13990000),
            ("Core i5/16GB/512GB", 17490000, 15490000),
        ),
        "attributes": {
            "Phân khúc": "Phổ thông",
            "Màn hình": "15.6 inch Full HD IPS",
            "Trọng lượng": "1,77 kg",
            "Nâng cấp": "Có khe RAM và SSD",
            "Nhu cầu": "Sinh viên, văn phòng, lập trình cơ bản",
            "Bảo hành": "12 tháng",
        },
        "review_strength": "hiệu năng ổn định, dễ nâng cấp và có nhiều cổng kết nối",
        "review_caveat": "màn hình chỉ ở mức đủ dùng cho chỉnh màu chuyên nghiệp",
    },
    {
        "name": "Tai nghe Samsung Galaxy Buds FE",
        "slug": "tai-nghe-samsung-galaxy-buds-fe",
        "category": ("Âm thanh", "am-thanh"),
        "brand": ("Samsung", "samsung"),
        "description": (
            "Tai nghe true wireless nhỏ gọn có chống ồn chủ động, wingtip bám tai và âm trầm "
            "dễ nghe. Sản phẩm phù hợp đi học, tập gym, gọi điện và người dùng điện thoại Galaxy "
            "cần một lựa chọn dưới 2 triệu đồng."
        ),
        "image": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.58",
        "rating_count": 176,
        "sold_count": 597,
        "variants": (("Graphite", 1990000, 1490000), ("Trắng", 1990000, 1590000)),
        "attributes": {
            "Kiểu tai nghe": "True wireless",
            "Chống ồn": "ANC chủ động",
            "Pin": "Tối đa 30 giờ cùng hộp sạc",
            "Chống nước": "IPX2",
            "Nhu cầu": "Đi học, tập gym, gọi điện",
            "Bảo hành": "12 tháng",
        },
        "review_strength": "đeo chắc tai, chống ồn khá và kết nối Galaxy nhanh",
        "review_caveat": "khả năng kháng nước chỉ phù hợp mồ hôi nhẹ",
    },
    {
        "name": "Tai nghe Anker Soundcore Liberty 4 NC",
        "slug": "tai-nghe-anker-soundcore-liberty-4-nc",
        "category": ("Âm thanh", "am-thanh"),
        "brand": ("Anker", "anker"),
        "description": (
            "Tai nghe không dây có chống ồn thích ứng, hỗ trợ LDAC và tùy chỉnh EQ sâu trong ứng "
            "dụng. Thời lượng pin dài, kết nối đa điểm và nhiều kích cỡ nút tai phù hợp làm việc "
            "tại quán cà phê, di chuyển bằng máy bay hoặc nghe nhạc hằng ngày."
        ),
        "image": "https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.71",
        "rating_count": 143,
        "sold_count": 421,
        "variants": (("Đen", 2490000, 1990000), ("Xanh navy", 2490000, 2090000)),
        "attributes": {
            "Kiểu tai nghe": "True wireless",
            "Chống ồn": "ANC thích ứng",
            "Codec": "LDAC, AAC, SBC",
            "Pin": "Tối đa 50 giờ cùng hộp sạc",
            "Nhu cầu": "Đi máy bay, làm việc, nghe nhạc",
            "Bảo hành": "18 tháng",
        },
        "review_strength": "chống ồn tốt trong tầm giá, pin lâu và EQ linh hoạt",
        "review_caveat": "hộp sạc bóng dễ bám dấu vân tay",
    },
    {
        "name": "Đồng hồ Garmin Forerunner 265",
        "slug": "dong-ho-garmin-forerunner-265",
        "category": ("Thiết bị đeo", "thiet-bi-deo"),
        "brand": ("Garmin", "garmin"),
        "description": (
            "Đồng hồ GPS chuyên chạy bộ với màn hình AMOLED, giáo án thích ứng và chỉ số phục hồi "
            "chuyên sâu. Thiết bị theo dõi nhịp tim, HRV, giấc ngủ và hỗ trợ ba môn phối hợp; pin "
            "nhiều ngày phù hợp người tập luyện nghiêm túc."
        ),
        "image": "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.86",
        "rating_count": 109,
        "sold_count": 238,
        "variants": (("42mm Đen", 11990000, 10490000), ("46mm Trắng", 11990000, 10690000)),
        "attributes": {
            "Màn hình": "AMOLED cảm ứng",
            "Định vị": "GPS đa băng tần",
            "Pin": "Tối đa 13 ngày",
            "Chống nước": "5 ATM",
            "Nhu cầu": "Chạy bộ, marathon, triathlon",
            "Bảo hành": "12 tháng",
        },
        "review_strength": "GPS chính xác, số liệu tập luyện sâu và pin tốt",
        "review_caveat": "nhiều chỉ số cần thời gian làm quen với người mới",
    },
    {
        "name": "Màn hình gaming LG UltraGear 27GR75Q-B",
        "slug": "man-hinh-gaming-lg-ultragear-27gr75q-b",
        "category": ("Màn hình", "man-hinh"),
        "brand": ("LG", "lg"),
        "description": (
            "Màn hình gaming 27 inch độ phân giải QHD, tấm nền IPS và tần số quét 165Hz. Thời gian "
            "phản hồi nhanh, hỗ trợ đồng bộ khung hình và chân đế điều chỉnh độ cao; phù hợp game "
            "FPS, MOBA và làm việc đa nhiệm."
        ),
        "image": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.69",
        "rating_count": 81,
        "sold_count": 193,
        "variants": (("27 inch", 7990000, 6690000),),
        "attributes": {
            "Kích thước": "27 inch",
            "Độ phân giải": "QHD 2560 x 1440",
            "Tấm nền": "IPS",
            "Tần số quét": "165Hz",
            "Nhu cầu": "Gaming FPS, MOBA, làm việc đa nhiệm",
            "Bảo hành": "24 tháng",
        },
        "review_strength": "hình ảnh mượt, màu đẹp và chân đế điều chỉnh tiện",
        "review_caveat": "độ tương phản màu đen chưa sâu như tấm nền VA hoặc OLED",
    },
    {
        "name": "Màn hình Dell UltraSharp U2723QE",
        "slug": "man-hinh-dell-ultrasharp-u2723qe",
        "category": ("Màn hình", "man-hinh"),
        "brand": ("Dell", "dell"),
        "description": (
            "Màn hình 4K 27 inch cho công việc sáng tạo và văn phòng chuyên nghiệp. Tấm nền IPS "
            "Black có độ tương phản cao, cổng USB-C cấp nguồn 90W và hub kết nối giúp dùng một dây "
            "với laptop; màu sắc phù hợp chỉnh ảnh và dựng nội dung."
        ),
        "image": "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.83",
        "rating_count": 73,
        "sold_count": 132,
        "variants": (("27 inch 4K", 16990000, 14990000),),
        "attributes": {
            "Kích thước": "27 inch",
            "Độ phân giải": "4K 3840 x 2160",
            "Tấm nền": "IPS Black",
            "Kết nối": "USB-C 90W, DisplayPort, HDMI, Ethernet",
            "Nhu cầu": "Chỉnh ảnh, thiết kế, văn phòng chuyên nghiệp",
            "Bảo hành": "36 tháng",
        },
        "review_strength": "màu sắc chính xác, hình ảnh sắc nét và hub USB-C rất tiện",
        "review_caveat": "tần số quét 60Hz không tối ưu cho game tốc độ cao",
    },
    {
        "name": "Máy ảnh Sony Alpha A6400",
        "slug": "may-anh-sony-alpha-a6400",
        "category": ("Máy ảnh", "may-anh"),
        "brand": ("Sony", "sony"),
        "description": (
            "Máy ảnh mirrorless cảm biến APS-C có lấy nét mắt thời gian thực và quay video 4K. "
            "Màn hình lật 180 độ phù hợp vlog, du lịch và chụp gia đình; hệ ống kính E-mount phong "
            "phú giúp người mới có thể nâng cấp lâu dài."
        ),
        "image": "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.79",
        "rating_count": 96,
        "sold_count": 167,
        "variants": (("Body", 20990000, 18990000), ("Kit 16-50mm", 23990000, 21490000)),
        "attributes": {
            "Cảm biến": "APS-C 24.2MP",
            "Video": "4K 30fps",
            "Lấy nét": "425 điểm, Eye AF",
            "Ngàm ống kính": "Sony E-mount",
            "Nhu cầu": "Vlog, du lịch, chân dung, gia đình",
            "Bảo hành": "24 tháng",
        },
        "review_strength": "lấy nét nhanh, ảnh nét và màn hình lật tiện quay vlog",
        "review_caveat": "thân máy không có chống rung cảm biến",
    },
    {
        "name": "Ổ cứng di động Samsung T7 Shield 1TB",
        "slug": "o-cung-di-dong-samsung-t7-shield-1tb",
        "category": ("Phụ kiện", "phu-kien"),
        "brand": ("Samsung", "samsung"),
        "description": (
            "SSD di động nhỏ gọn đạt tốc độ đọc khoảng 1.050 MB/s, có vỏ cao su chống sốc và "
            "chuẩn kháng nước IP65. Phù hợp sao lưu ảnh, dựng video trực tiếp, mang dữ liệu giữa "
            "máy Windows, macOS và thiết bị di động hỗ trợ USB-C."
        ),
        "image": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.84",
        "rating_count": 129,
        "sold_count": 344,
        "variants": (("1TB Đen", 3490000, 2890000), ("2TB Xanh", 5990000, 5190000)),
        "attributes": {
            "Dung lượng": "1TB hoặc 2TB",
            "Tốc độ đọc": "Tối đa 1.050 MB/s",
            "Kết nối": "USB 3.2 Gen 2 Type-C",
            "Chống nước": "IP65",
            "Nhu cầu": "Sao lưu, dựng video, di chuyển dữ liệu",
            "Bảo hành": "36 tháng",
        },
        "review_strength": "tốc độ ổn định, nhỏ gọn và vỏ chống va đập tốt",
        "review_caveat": "vỏ cao su dễ bám bụi sau thời gian sử dụng",
    },
    {
        "name": "Pin sạc dự phòng Anker 737 Power Bank",
        "slug": "pin-sac-du-phong-anker-737-power-bank",
        "category": ("Phụ kiện", "phu-kien"),
        "brand": ("Anker", "anker"),
        "description": (
            "Pin dự phòng dung lượng 24.000 mAh, công suất USB-C tối đa 140W và màn hình hiển thị "
            "thông số sạc. Thiết bị có thể cấp nguồn cho laptop, máy tính bảng và điện thoại khi "
            "đi công tác; hệ thống bảo vệ nhiệt phù hợp nhu cầu sạc nhiều thiết bị."
        ),
        "image": "https://unsplash.com/photos/UP_RojtnvTU/download?force=true&w=1200",
        "rating": "4.76",
        "rating_count": 112,
        "sold_count": 286,
        "variants": (("24.000mAh Đen", 4290000, 3690000),),
        "attributes": {
            "Dung lượng": "24.000 mAh",
            "Công suất": "Tối đa 140W USB-C PD 3.1",
            "Cổng sạc": "2 USB-C, 1 USB-A",
            "Trọng lượng": "630 g",
            "Nhu cầu": "Sạc laptop, công tác, nhiều thiết bị",
            "Bảo hành": "24 tháng",
        },
        "review_strength": "sạc được laptop, công suất cao và màn hình thông tin hữu ích",
        "review_caveat": "trọng lượng khá nặng để mang hằng ngày",
    },
    {
        "name": "Robot hút bụi lau nhà Xiaomi Robot Vacuum S10",
        "slug": "robot-hut-bui-lau-nha-xiaomi-s10",
        "category": ("Gia dụng thông minh", "gia-dung-thong-minh"),
        "brand": ("Xiaomi", "xiaomi"),
        "description": (
            "Robot hút bụi và lau nhà dùng điều hướng laser LDS, lực hút 4.000 Pa và bản đồ nhiều "
            "tầng. Ứng dụng cho phép đặt vùng cấm, lịch dọn và điều chỉnh lượng nước; phù hợp căn "
            "hộ có sàn gỗ, gạch, thú cưng và diện tích dưới 120 m²."
        ),
        "image": "https://images.unsplash.com/photo-1558317374-067fb5f30001?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.66",
        "rating_count": 147,
        "sold_count": 319,
        "variants": (("Trắng", 7990000, 6490000), ("Đen", 7990000, 6690000)),
        "attributes": {
            "Lực hút": "4.000 Pa",
            "Điều hướng": "Laser LDS, bản đồ nhiều tầng",
            "Diện tích phù hợp": "Dưới 120 m²",
            "Tính năng": "Hút bụi, lau nhà, vùng cấm",
            "Nhu cầu": "Căn hộ, nhà có thú cưng, sàn gỗ",
            "Bảo hành": "18 tháng",
        },
        "review_strength": "lập bản đồ nhanh, hút tóc thú cưng tốt và ứng dụng dễ dùng",
        "review_caveat": "chức năng lau phù hợp duy trì hằng ngày hơn là xử lý vết bẩn khô",
    },
    {
        "name": "Nồi chiên không dầu Philips HD9252/90",
        "slug": "noi-chien-khong-dau-philips-hd9252-90",
        "category": ("Thiết bị nhà bếp", "thiet-bi-nha-bep"),
        "brand": ("Philips", "philips"),
        "description": (
            "Nồi chiên không dầu dung tích 4,1 lít sử dụng công nghệ Rapid Air, bảng điều khiển "
            "cảm ứng và bảy chương trình cài sẵn. Kích thước phù hợp gia đình hai đến bốn người, "
            "có thể chiên khoai, nướng thịt và hâm nóng với ít dầu."
        ),
        "image": "https://images.unsplash.com/photo-1585515320310-259814833e62?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.72",
        "rating_count": 215,
        "sold_count": 804,
        "variants": (("4.1 lít Đen", 3290000, 2490000),),
        "attributes": {
            "Dung tích": "4,1 lít",
            "Công suất": "1.400W",
            "Điều khiển": "Cảm ứng, 7 chương trình",
            "Số người phù hợp": "2 đến 4 người",
            "Nhu cầu": "Chiên ít dầu, nướng, hâm nóng",
            "Bảo hành": "24 tháng",
        },
        "review_strength": "thức ăn chín đều, thao tác dễ và vệ sinh nhanh",
        "review_caveat": "dung tích hơi nhỏ nếu nấu cho gia đình trên bốn người",
    },
    {
        "name": "Máy pha cà phê De'Longhi Dedica EC685",
        "slug": "may-pha-ca-phe-delonghi-dedica-ec685",
        "category": ("Thiết bị nhà bếp", "thiet-bi-nha-bep"),
        "brand": ("De'Longhi", "delonghi"),
        "description": (
            "Máy pha espresso thân hẹp dùng bơm áp suất 15 bar, hỗ trợ cà phê bột và pod ESE. "
            "Vòi đánh sữa thủ công cho cappuccino, thời gian làm nóng nhanh và khay cốc "
            "điều chỉnh; "
            "phù hợp người mới bắt đầu pha cà phê tại nhà."
        ),
        "image": "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.74",
        "rating_count": 103,
        "sold_count": 226,
        "variants": (("Bạc", 6990000, 5790000), ("Đỏ", 6990000, 5990000)),
        "attributes": {
            "Áp suất": "15 bar",
            "Loại cà phê": "Cà phê bột và pod ESE",
            "Đánh sữa": "Vòi hơi thủ công",
            "Kích thước": "Rộng 15 cm",
            "Nhu cầu": "Espresso, cappuccino tại nhà",
            "Bảo hành": "24 tháng",
        },
        "review_strength": "máy nhỏ gọn, làm nóng nhanh và espresso có crema tốt",
        "review_caveat": "cần luyện thao tác đánh sữa để có bọt mịn",
    },
    {
        "name": "Giày chạy bộ Nike Pegasus 41",
        "slug": "giay-chay-bo-nike-pegasus-41",
        "category": ("Thể thao", "the-thao"),
        "brand": ("Nike", "nike"),
        "description": (
            "Giày chạy bộ hằng ngày có đệm ReactX kết hợp hai túi khí Air Zoom, thân giày lưới "
            "thoáng và đế ngoài bền. Form cân bằng phù hợp người mới, chạy phục hồi, tập 5–10 km "
            "và sử dụng đi bộ; không phải mẫu chuyên thi đấu tốc độ."
        ),
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.70",
        "rating_count": 189,
        "sold_count": 476,
        "variants": (
            ("Size 40 Đen", 3690000, 3190000),
            ("Size 42 Trắng", 3690000, 3290000),
            ("Size 44 Xanh", 3690000, 3290000),
        ),
        "attributes": {
            "Loại giày": "Giày chạy bộ hằng ngày",
            "Đệm": "ReactX và Air Zoom",
            "Cự ly phù hợp": "5 đến 10 km",
            "Bề mặt": "Đường nhựa, máy chạy bộ",
            "Nhu cầu": "Người mới chạy, chạy phục hồi, đi bộ",
            "Bảo hành": "6 tháng",
        },
        "review_strength": "đệm êm vừa phải, form ổn định và dùng hằng ngày thoải mái",
        "review_caveat": "trọng lượng không nhẹ bằng giày chuyên chạy tốc độ",
    },
    {
        "name": "Kem chống nắng La Roche-Posay Anthelios UVMune 400",
        "slug": "kem-chong-nang-la-roche-posay-anthelios-uvmune-400",
        "category": ("Chăm sóc da", "cham-soc-da"),
        "brand": ("La Roche-Posay", "la-roche-posay"),
        "description": (
            "Kem chống nắng phổ rộng SPF50+ PA++++ bảo vệ trước tia UVA dài, kết cấu dạng fluid "
            "nhẹ và không để lại vệt trắng rõ. Công thức không hương liệu, phù hợp da nhạy cảm và "
            "da hỗn hợp; nên thoa lại sau khi đổ mồ hôi hoặc hoạt động ngoài trời lâu."
        ),
        "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.64",
        "rating_count": 268,
        "sold_count": 1052,
        "variants": (("Không màu 50ml", 599000, 459000), ("Có màu 50ml", 629000, 489000)),
        "attributes": {
            "Chỉ số chống nắng": "SPF50+ PA++++",
            "Kết cấu": "Fluid lỏng nhẹ",
            "Loại da": "Da nhạy cảm, da hỗn hợp",
            "Hương liệu": "Không hương liệu",
            "Nhu cầu": "Chống nắng hằng ngày, hoạt động ngoài trời",
            "Dung tích": "50 ml",
        },
        "review_strength": "chất lỏng nhẹ, không cay mắt và bảo vệ tốt khi đi ngoài trời",
        "review_caveat": "có thể hơi bóng trên da rất dầu nếu thoa lượng nhiều",
    },
    {
        "name": "Ghế công thái học Sihoo M57",
        "slug": "ghe-cong-thai-hoc-sihoo-m57",
        "category": ("Nội thất văn phòng", "noi-that-van-phong"),
        "brand": ("Sihoo", "sihoo"),
        "description": (
            "Ghế công thái học lưng lưới có tựa đầu, kê tay 3D và hỗ trợ thắt lưng điều chỉnh. "
            "Mâm ngồi rộng, ngả lưng nhiều mức và phù hợp bàn làm việc tại nhà; khuyến nghị cho "
            "người cao khoảng 1,60–1,85 m, ngồi từ sáu đến tám giờ mỗi ngày."
        ),
        "image": "https://images.unsplash.com/photo-1580480055273-228ff5388ef8?auto=format&fit=crop&w=1200&q=80",
        "rating": "4.57",
        "rating_count": 137,
        "sold_count": 298,
        "variants": (("Đen", 4990000, 3990000), ("Xám", 5190000, 4190000)),
        "attributes": {
            "Chất liệu": "Lưới thoáng khí",
            "Kê tay": "Điều chỉnh 3D",
            "Tải trọng": "Tối đa 150 kg",
            "Chiều cao phù hợp": "1,60 đến 1,85 m",
            "Nhu cầu": "Làm việc tại nhà, ngồi 6 đến 8 giờ",
            "Bảo hành": "36 tháng khung ghế",
        },
        "review_strength": "lưng lưới thoáng, hỗ trợ thắt lưng tốt và nhiều vị trí điều chỉnh",
        "review_caveat": "khâu lắp ráp ban đầu cần hai người để thao tác dễ hơn",
    },
)


EXISTING_PRODUCT_ATTRIBUTES = {
    "dien-thoai-galaxy-s24-ultra-5g": {
        "Phân khúc": "Cao cấp",
        "Màn hình": "6.8 inch AMOLED 120Hz",
        "Camera": "200MP, zoom quang học, chống rung OIS",
        "Bút cảm ứng": "S Pen tích hợp",
        "Nhu cầu": "Chụp ảnh, ghi chú, làm việc, chơi game",
        "Chống nước": "IP68",
    },
    "dien-thoai-iphone-15-pro-max": {
        "Phân khúc": "Cao cấp",
        "Màn hình": "6.7 inch OLED 120Hz",
        "Camera": "48MP, quay video ProRes, zoom quang 5x",
        "Chất liệu": "Khung titan",
        "Nhu cầu": "Quay video, chụp ảnh, hệ sinh thái Apple",
        "Chống nước": "IP68",
    },
    "laptop-macbook-air-m3-13-inch": {
        "Phân khúc": "Ultrabook",
        "Màn hình": "13.6 inch Liquid Retina",
        "Trọng lượng": "1,24 kg",
        "Pin": "Tối đa 18 giờ",
        "Nhu cầu": "Học tập, văn phòng, lập trình, sáng tạo nội dung",
        "Hệ điều hành": "macOS",
    },
    "laptop-dell-xps-13-plus": {
        "Phân khúc": "Ultrabook cao cấp",
        "Màn hình": "13.4 inch",
        "Trọng lượng": "1,26 kg",
        "Kết nối": "Thunderbolt 4",
        "Nhu cầu": "Văn phòng, doanh nhân, di chuyển",
        "Hệ điều hành": "Windows 11",
    },
    "tai-nghe-sony-wh-1000xm5": {
        "Kiểu tai nghe": "Chụp tai không dây",
        "Chống ồn": "ANC cao cấp",
        "Pin": "Tối đa 30 giờ",
        "Kết nối": "Bluetooth đa điểm, LDAC",
        "Nhu cầu": "Đi máy bay, làm việc, nghe nhạc",
    },
    "tai-nghe-airpods-pro-the-he-2": {
        "Kiểu tai nghe": "True wireless",
        "Chống ồn": "ANC và xuyên âm thích ứng",
        "Pin": "Tối đa 30 giờ cùng hộp sạc",
        "Chống nước": "IP54",
        "Nhu cầu": "Hệ sinh thái Apple, gọi điện, di chuyển",
    },
    "dong-ho-apple-watch-series-9": {
        "Màn hình": "OLED Always-On",
        "Kết nối": "GPS, Bluetooth, Wi-Fi",
        "Pin": "Khoảng 18 giờ",
        "Chống nước": "50 m",
        "Nhu cầu": "Theo dõi sức khỏe, luyện tập, hệ sinh thái Apple",
    },
    "dong-ho-samsung-galaxy-watch6": {
        "Màn hình": "Super AMOLED",
        "Kết nối": "GPS, Bluetooth, Wi-Fi",
        "Pin": "Khoảng 40 giờ",
        "Chống nước": "5 ATM, IP68",
        "Nhu cầu": "Theo dõi sức khỏe, tập gym, Android",
    },
    "loa-bluetooth-jbl-charge-5": {
        "Công suất": "40W",
        "Pin": "Tối đa 20 giờ",
        "Chống nước": "IP67",
        "Kết nối": "Bluetooth 5.1",
        "Nhu cầu": "Dã ngoại, tiệc nhỏ, nghe nhạc ngoài trời",
    },
    "may-tinh-bang-ipad-air-m2": {
        "Màn hình": "11 inch Liquid Retina",
        "Vi xử lý": "Apple M2",
        "Phụ kiện hỗ trợ": "Apple Pencil Pro, Magic Keyboard",
        "Nhu cầu": "Học tập, ghi chú, vẽ, chỉnh ảnh",
        "Hệ điều hành": "iPadOS",
    },
    "ban-phim-co-keychron-k2-pro": {
        "Layout": "75% 84 phím",
        "Kết nối": "Bluetooth, USB-C",
        "Switch": "Red hoặc Brown",
        "Tương thích": "Windows, macOS, Linux",
        "Nhu cầu": "Gõ văn bản, lập trình, gaming",
    },
    "chuot-khong-day-logitech-mx-master-3s": {
        "Cảm biến": "8.000 DPI",
        "Kết nối": "Bluetooth, Logi Bolt",
        "Pin": "Tối đa 70 ngày",
        "Tương thích": "Windows, macOS, Linux",
        "Nhu cầu": "Văn phòng, thiết kế, làm việc đa thiết bị",
    },
}

DEFAULT_REVIEW_CAVEATS = {
    "Điện thoại": "giá phụ kiện chính hãng còn cao",
    "Laptop": "bộ sạc đi kèm chiếm khá nhiều chỗ trong balo",
    "Âm thanh": "cần chỉnh EQ để hợp gu nghe cá nhân",
    "Thiết bị đeo": "cần sạc thường xuyên nếu bật theo dõi liên tục",
    "Phụ kiện": "mức giá cao hơn sản phẩm phổ thông",
}


class Command(BaseCommand):
    help = (
        "Seed approved demo products with variants, structured attributes, inventory, "
        "and verified reviews for manual AI testing."
    )

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
        parser.add_argument(
            "--reviews-per-product",
            type=int,
            default=5,
            help="Verified demo reviews per product (0-5). Use 0 to skip review data.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        stock = options["stock"]
        reviews_per_product = options["reviews_per_product"]
        if not 1 <= count <= len(PRODUCTS):
            raise CommandError(f"count must be between 1 and {len(PRODUCTS)}")
        if stock < 0:
            raise CommandError("stock must be non-negative")
        if not 0 <= reviews_per_product <= 5:
            raise CommandError("reviews-per-product must be between 0 and 5")

        shop = self._get_shop()
        created_products = 0
        created_variants = 0
        created_attribute_links = 0
        seeded_products = []

        for product_number, data in enumerate(PRODUCTS[:count], start=1):
            category = self._get_category(*data["category"])
            brand = self._get_brand(*data["brand"])
            prices = [Decimal(str(variant[2])) for variant in data["variants"]]
            product_variants = []
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
                product_variants.append(variant)
                InventoryBalance.objects.get_or_create(
                    variant=variant,
                    defaults={
                        "available_stock": stock,
                        "reserved_stock": 0,
                        "low_stock_threshold": 5,
                    },
                )

            attributes = {
                **EXISTING_PRODUCT_ATTRIBUTES.get(data["slug"], {}),
                **data.get("attributes", {}),
                "Tùy chọn": ", ".join(variant[0] for variant in data["variants"]),
            }
            created_attribute_links += self._seed_product_attributes(
                shop=shop,
                product=product,
                attributes=attributes,
            )
            seeded_products.append((product_number, product, data, product_variants[0]))

        created_reviews = self._seed_reviews(
            shop=shop,
            seeded_products=seeded_products,
            reviews_per_product=reviews_per_product,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {count} products for '{shop.name}' "
                f"({created_products} products, {created_variants} variants, "
                f"{created_attribute_links} attribute links, and {created_reviews} reviews "
                "created)."
            )
        )

    @staticmethod
    def _seed_product_attributes(
        *,
        shop: Shop,
        product: Product,
        attributes: dict[str, str],
    ) -> int:
        attribute_values = []
        for sort_order, (name, value) in enumerate(attributes.items(), start=1):
            attribute, _ = Attribute.objects.update_or_create(
                shop=shop,
                name=name,
                defaults={
                    "code": slugify(name)[:100],
                    "display_type": Attribute.DisplayType.TEXT,
                    "sort_order": sort_order,
                },
            )
            attribute_value, _ = AttributeValue.objects.update_or_create(
                attribute=attribute,
                value=value,
                defaults={
                    "display_value": value,
                    "sort_order": sort_order,
                },
            )
            attribute_values.append(attribute_value)

        existing_value_ids = set(
            ProductAttributeValue.objects.filter(
                product=product,
                attribute_value__in=attribute_values,
            ).values_list("attribute_value_id", flat=True)
        )
        missing_links = [
            ProductAttributeValue(product=product, attribute_value=attribute_value)
            for attribute_value in attribute_values
            if attribute_value.pk not in existing_value_ids
        ]
        ProductAttributeValue.objects.bulk_create(
            missing_links,
            ignore_conflicts=True,
        )
        return len(missing_links)

    @classmethod
    def _seed_reviews(
        cls,
        *,
        shop: Shop,
        seeded_products: list[tuple[int, Product, dict, ProductVariant]],
        reviews_per_product: int,
    ) -> int:
        if reviews_per_product == 0:
            return 0

        created_reviews = 0
        subtotal = sum(variant.sale_price for _, _, _, variant in seeded_products)
        for reviewer_number in range(1, reviews_per_product + 1):
            reviewer = cls._get_reviewer(reviewer_number)
            customer = CustomerProfile.objects.get(user=reviewer)
            order, _ = Order.objects.update_or_create(
                order_code=f"ORD-AI-DEMO-{reviewer_number:02d}",
                defaults={
                    "customer": customer,
                    "subtotal": subtotal,
                    "platform_discount": Decimal("0"),
                    "shop_discount_total": Decimal("0"),
                    "shipping_total": Decimal("0"),
                    "grand_total": subtotal,
                    "payment_status": Order.PaymentStatus.PAID,
                    "payment_method": Order.PaymentMethod.COD,
                    "idempotency_key": f"seed-products-ai-review-{reviewer_number:02d}",
                    "checkout_note": "Đơn hàng demo phục vụ kiểm thử tính năng AI.",
                },
            )
            shop_order, _ = ShopOrder.objects.update_or_create(
                order=order,
                shop=shop,
                defaults={
                    "shop_order_code": f"SORD-AI-DEMO-{reviewer_number:02d}",
                    "fulfillment_status": ShopOrder.FulfillmentStatus.COMPLETED,
                    "subtotal": subtotal,
                    "shop_discount": Decimal("0"),
                    "platform_discount_allocated": Decimal("0"),
                    "shipping_fee": Decimal("0"),
                    "total_amount": subtotal,
                    "shipping_method_code": "DEMO",
                    "shipping_method_name": "Giao hàng dữ liệu mẫu",
                    "delivered_at": timezone.now(),
                    "completed_at": timezone.now(),
                },
            )

            for product_number, product, data, variant in seeded_products:
                item, _ = OrderItem.objects.update_or_create(
                    shop_order=shop_order,
                    sku=f"AI-REVIEW-{reviewer_number:02d}-{product_number:02d}",
                    defaults={
                        "product": product,
                        "variant": variant,
                        "product_name": product.name,
                        "variant_name": variant.name or "",
                        "variant_attributes": {},
                        "product_image_url": data["image"],
                        "unit_original_price": variant.original_price,
                        "unit_sale_price": variant.sale_price,
                        "quantity": 1,
                        "line_subtotal": variant.sale_price,
                        "shop_discount": Decimal("0"),
                        "platform_discount": Decimal("0"),
                        "line_total": variant.sale_price,
                        "cost_price_snapshot": variant.cost_price,
                    },
                )
                _, review_created = Review.objects.update_or_create(
                    order_item=item,
                    defaults={
                        "product": product,
                        "user": reviewer,
                        "rating": cls._review_rating(data["rating"], reviewer_number),
                        "content": cls._review_content(
                            data=data,
                            reviewer_number=reviewer_number,
                        ),
                        "is_verified_purchase": True,
                        "status": Review.Status.VISIBLE,
                        "is_deleted": False,
                        "deleted_at": None,
                    },
                )
                created_reviews += int(review_created)

        for _, product, _, _ in seeded_products:
            stats = Review.objects.filter(
                product=product,
                status=Review.Status.VISIBLE,
                is_deleted=False,
            ).aggregate(average=Avg("rating"), count=Count("id"))
            Product.objects.filter(pk=product.pk).update(
                rating_average=Decimal(str(stats["average"] or 0)).quantize(Decimal("0.01")),
                rating_count=stats["count"],
            )
        return created_reviews

    @staticmethod
    def _get_reviewer(reviewer_number: int) -> User:
        reviewer, created = User.objects.get_or_create(
            email=f"ai-reviewer-{reviewer_number:02d}@example.com",
            defaults={
                "role": User.Role.CUSTOMER,
                "full_name": f"Khách hàng AI {reviewer_number:02d}",
                "is_active": True,
                "is_email_verified": True,
            },
        )
        update_fields = []
        if created or not reviewer.password:
            reviewer.set_unusable_password()
            update_fields.append("password")
        if reviewer.role != User.Role.CUSTOMER:
            reviewer.role = User.Role.CUSTOMER
            update_fields.append("role")
        if not reviewer.is_active:
            reviewer.is_active = True
            update_fields.append("is_active")
        if not reviewer.is_email_verified:
            reviewer.is_email_verified = True
            update_fields.append("is_email_verified")
        if update_fields:
            reviewer.save(update_fields=[*update_fields, "updated_at"])
        CustomerProfile.objects.get_or_create(user=reviewer)
        return reviewer

    @staticmethod
    def _review_rating(target_rating: str, reviewer_number: int) -> int:
        target = Decimal(target_rating)
        if target >= Decimal("4.80"):
            ratings = (5, 5, 5, 5, 4)
        elif target >= Decimal("4.60"):
            ratings = (5, 5, 5, 4, 4)
        else:
            ratings = (5, 5, 4, 4, 4)
        return ratings[reviewer_number - 1]

    @staticmethod
    def _review_content(*, data: dict, reviewer_number: int) -> str:
        category_name = data["category"][0]
        strength = data.get("review_strength") or data["description"].split(".", maxsplit=1)[0]
        caveat = data.get("review_caveat") or DEFAULT_REVIEW_CAVEATS.get(
            category_name,
            "cần thêm thời gian sử dụng để đánh giá độ bền lâu dài",
        )
        templates = (
            f"Đã dùng {data['name']} hơn hai tuần. {strength.capitalize()}. "
            "Sản phẩm đúng mô tả và giao hàng cẩn thận.",
            f"Trải nghiệm tổng thể tốt: {strength}. Điểm cần cân nhắc là {caveat}.",
            "Mua để phục vụ nhu cầu "
            f"{data.get('attributes', {}).get('Nhu cầu', 'hằng ngày')}. "
            f"{strength.capitalize()}, thao tác làm quen nhanh.",
            f"Sản phẩm hoạt động ổn định và thông tin trên trang khá đầy đủ. Tuy nhiên, {caveat}.",
            f"Sau thời gian sử dụng thực tế, tôi hài lòng vì {strength}. "
            "Sẽ giới thiệu cho người có nhu cầu tương tự.",
        )
        return templates[reviewer_number - 1]

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

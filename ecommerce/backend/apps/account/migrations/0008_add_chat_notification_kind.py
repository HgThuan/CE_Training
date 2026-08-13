from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("account", "0007_alter_notification_kind")]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="kind",
            field=models.CharField(
                choices=[
                    ("seller_application", "Hồ sơ seller"),
                    ("document_review", "Xác minh giấy tờ"),
                    ("shop_status", "Trạng thái gian hàng"),
                    ("inventory_low_stock", "Tồn kho thấp"),
                    ("back_in_stock", "Có hàng trở lại"),
                    ("order", "Đơn hàng"),
                    ("chat", "Tin nhắn"),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
    ]

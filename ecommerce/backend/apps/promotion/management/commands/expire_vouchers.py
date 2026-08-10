from django.core.management.base import BaseCommand

from apps.promotion.services import UserVoucherService


class Command(BaseCommand):
    help = "Expire saved vouchers and release pending voucher locks past their TTL."

    def handle(self, *args, **options):
        count = UserVoucherService.expire_vouchers()
        self.stdout.write(self.style.SUCCESS(f"Expired {count} voucher(s)."))

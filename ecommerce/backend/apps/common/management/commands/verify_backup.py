import hashlib
import json
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Verify a backup checksum and ensure pg_restore can read its catalog"

    def add_arguments(self, parser):
        parser.add_argument("backup")

    def handle(self, *args, **options):
        root = Path(settings.BACKUP_ROOT).resolve()
        backup = (root / options["backup"]).resolve()
        if backup.parent != root or backup.suffix != ".dump" or not backup.is_file():
            raise CommandError("Backup must be an existing .dump file inside BACKUP_ROOT")
        manifest_path = backup.with_suffix(".json")
        if not manifest_path.is_file():
            raise CommandError("Backup manifest is missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(backup.read_bytes()).hexdigest()
        if digest != manifest.get("sha256"):
            raise CommandError("Backup checksum mismatch")
        try:
            subprocess.run(["pg_restore", "--list", str(backup)], check=True, capture_output=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise CommandError(f"Backup catalog verification failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Backup verified: {backup.name}"))

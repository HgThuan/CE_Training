import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restore a verified backup into a separate PostgreSQL database"

    def add_arguments(self, parser):
        parser.add_argument("backup")
        parser.add_argument("--database", required=True)
        parser.add_argument("--confirm", default="")

    def handle(self, *args, **options):
        backup_root = Path(settings.BACKUP_ROOT).resolve()
        backup = (backup_root / options["backup"]).resolve()
        target_database = options["database"].strip()
        current_database = str(settings.DATABASES["default"]["NAME"])
        if backup.parent != backup_root or backup.suffix != ".dump" or not backup.is_file():
            raise CommandError("Backup must be an existing .dump file inside BACKUP_ROOT")
        if not target_database or target_database == current_database:
            raise CommandError("Restore target must be a separate, non-production database")
        if options["confirm"] != target_database:
            raise CommandError("Pass --confirm with the exact target database name")

        database = settings.DATABASES["default"]
        command = [
            "pg_restore",
            "--exit-on-error",
            "--no-owner",
            "--host",
            str(database["HOST"]),
            "--port",
            str(database["PORT"]),
            "--username",
            str(database["USER"]),
            "--dbname",
            target_database,
            str(backup),
        ]
        environment = {**os.environ, "PGPASSWORD": str(database["PASSWORD"])}
        try:
            subprocess.run(command, check=True, env=environment, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise CommandError(f"Restore failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Restored {backup.name} into {target_database}"))

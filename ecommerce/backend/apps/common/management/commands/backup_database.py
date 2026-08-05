import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a PostgreSQL custom-format backup and SHA-256 manifest"

    def add_arguments(self, parser):
        parser.add_argument("--name", default="")

    def handle(self, *args, **options):
        backup_root = Path(settings.BACKUP_ROOT).resolve()
        backup_root.mkdir(parents=True, exist_ok=True)
        name = options["name"].strip() or datetime.now(UTC).strftime("mercato-%Y%m%dT%H%M%SZ")
        if not name.replace("-", "").replace("_", "").isalnum():
            raise CommandError("Backup name may only contain letters, numbers, '-' and '_'")
        target = (backup_root / f"{name}.dump").resolve()
        if target.parent != backup_root:
            raise CommandError("Invalid backup path")
        database = settings.DATABASES["default"]
        command = [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--file",
            str(target),
            "--host",
            str(database["HOST"]),
            "--port",
            str(database["PORT"]),
            "--username",
            str(database["USER"]),
            str(database["NAME"]),
        ]
        env = {**os.environ, "PGPASSWORD": str(database["PASSWORD"])}
        try:
            subprocess.run(command, check=True, env=env, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            target.unlink(missing_ok=True)
            raise CommandError(f"Backup failed: {exc}") from exc
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        manifest = {
            "file": target.name,
            "sha256": digest,
            "created_at": datetime.now(UTC).isoformat(),
            "database": database["NAME"],
        }
        target.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Backup created: {target}"))

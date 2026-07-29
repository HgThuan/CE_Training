from django.core.management.base import BaseCommand, CommandError

from apps.ai.embedding_service import EmbeddingService
from apps.ai.services import AIService
from apps.ai.tasks import reindex_all_products
from apps.product.selectors import ProductSelector


class Command(BaseCommand):
    help = "Index embeddings for all public products."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Database iterator and dispatch batch size (1-1000).",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run indexing in this process instead of dispatching Celery tasks.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        if not 1 <= batch_size <= 1_000:
            raise CommandError("--batch-size must be between 1 and 1000.")
        if not AIService.is_configured() or not EmbeddingService.is_enabled():
            raise CommandError(
                "AI embedding indexing is disabled or the provider is not configured; "
                "no embedding request was sent."
            )

        if not options["sync"]:
            task = reindex_all_products.delay(batch_size=batch_size)
            self.stdout.write(
                self.style.SUCCESS(f"Queued full embedding reindex (task_id={task.id}).")
            )
            return

        indexed = unchanged = unavailable = removed = 0
        product_ids = (
            ProductSelector.public_base()
            .order_by("pk")
            .values_list("pk", flat=True)
            .iterator(chunk_size=batch_size)
        )
        for product_id in product_ids:
            result = EmbeddingService.index_product(product_id)
            if result.status == "indexed":
                indexed += 1
            elif result.status == "unchanged":
                unchanged += 1
            elif result.status == "removed":
                removed += 1
            else:
                unavailable += 1
        self.stdout.write(
            self.style.SUCCESS(
                "Embedding reindex complete: "
                f"indexed={indexed}, unchanged={unchanged}, "
                f"unavailable={unavailable}, removed={removed}."
            )
        )

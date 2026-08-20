from django.core.management.base import BaseCommand, CommandError

from apps.ai.models import AIRequestLog, PolicyDocument
from apps.ai.services import AIService


class Command(BaseCommand):
    help = "Generate embeddings for active, verified shopping policy documents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rebuild embeddings that already exist.",
        )

    def handle(self, *args, **options):
        if not AIService.is_configured():
            raise CommandError("AI provider is disabled or not configured")

        queryset = PolicyDocument.objects.filter(is_active=True).order_by("category", "id")
        if not options["force"]:
            queryset = queryset.filter(embedding__isnull=True)

        service = AIService()
        indexed = 0
        for document in queryset.iterator(chunk_size=100):
            result = service.get_embedding(
                feature=AIRequestLog.Feature.POLICY_EMBEDDING,
                text=document.content,
                title=document.title,
                task_type="retrieval_document",
                fallback=[],
                cache_ttl=0,
            )
            if not result.ai_used or result.fallback_used or not result.vector:
                self.stderr.write(f"Skipped {document.pk}: provider did not return an embedding")
                continue
            PolicyDocument.objects.filter(pk=document.pk).update(embedding=result.vector)
            indexed += 1

        self.stdout.write(self.style.SUCCESS(f"Indexed {indexed} policy documents"))

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.account.models import Notification

from .services import NotificationService


@receiver(post_save, sender=Notification)
def push_new_notification(sender, instance, created, **kwargs):
    if created and not instance.is_deleted:
        transaction.on_commit(lambda: NotificationService.broadcast(instance.pk))

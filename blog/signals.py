from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.images.models import Image

from blog.tasks import convert_image_to_avif


@receiver(post_save, sender=Image)
def image_post_save(sender, instance, created, **kwargs):
    if created:
        convert_image_to_avif.delay(instance.id)

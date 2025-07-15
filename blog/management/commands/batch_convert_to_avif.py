from django.core.management.base import BaseCommand
from wagtail.images.models import Image

from blog.tasks import convert_image_to_avif


class Command(BaseCommand):
    help = "Trigger Celery task to convert all images to AVIF"

    def handle(self, *args, **options):
        total = Image.objects.count()
        self.stdout.write(f"Found {total} images to convert...")

        for i, img in enumerate(Image.objects.all()):
            convert_image_to_avif.delay(img.id)
            self.stdout.write(f"Queued image {i + 1}/{total}: {img.title}")

        self.stdout.write(self.style.SUCCESS("All tasks queued!"))

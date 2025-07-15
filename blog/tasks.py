import os
from io import BytesIO
from celery import shared_task
from PIL import Image
from wagtail.images.models import Image as WagtailImage
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


@shared_task
def convert_image_to_avif(image_id):
    try:
        wagtail_image = WagtailImage.objects.get(id=image_id)

        # Open original image via storage
        with wagtail_image.file.open() as f:
            pil_img = Image.open(f)

            # Convert to RGB if needed
            if pil_img.mode in ("RGBA", "P"):
                pil_img = pil_img.convert("RGBA")
            else:
                pil_img = pil_img.convert("RGB")

            # Save as AVIF
            buffer = BytesIO()
            pil_img.save(buffer, format="AVIF", quality=70)
            avif_content = ContentFile(buffer.getvalue())

        # Use original file name
        original_name = wagtail_image.file.name
        base_name, _ = os.path.splitext(original_name)
        avif_filename = f"{base_name}.avif"

        # Save to avif_images/
        avif_path = f"avif_images/{avif_filename}"

        # Optional: delete existing file first if overwriting
        if default_storage.exists(avif_path):
            default_storage.delete(avif_path)

        avif_path = default_storage.save(avif_path, avif_content)

        return {
            "status": "success",
            "image_id": image_id,
            "avif_url": default_storage.url(avif_path),
            "avif_path": avif_path,
        }

    except Exception as e:
        return {
            "status": "error",
            "image_id": image_id,
            "message": str(e),
        }

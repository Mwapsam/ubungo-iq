import os
from io import BytesIO
from celery import shared_task
from PIL import Image
from wagtail.images.models import Image as WagtailImage
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.db import models
import logging

logger = logging.getLogger(__name__)


@shared_task
def convert_image_to_avif(image_id):
    try:
        wagtail_image = WagtailImage.objects.get(id=image_id)
        with wagtail_image.file.open() as f:
            pil_img = Image.open(f)
            if pil_img.mode in ("RGBA", "P"):
                pil_img = pil_img.convert("RGBA")
            else:
                pil_img = pil_img.convert("RGB")
            buffer = BytesIO()
            pil_img.save(buffer, format="AVIF", quality=70)
            avif_content = ContentFile(buffer.getvalue())
        original_name = wagtail_image.file.name
        base_name, _ = os.path.splitext(original_name)
        avif_filename = f"{base_name}.avif"
        avif_path = f"avif_images/{avif_filename}"
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


@shared_task(bind=True, max_retries=3)
def increment_view_count_async(self, page_id, ip_address, user_agent=None):
    try:
        view_key = f"view_counted:{page_id}:{ip_address}"
        
        if cache.get(view_key):
            logger.debug(f"View already counted for IP {ip_address} on page {page_id}")
            return False
        
        cache.set(view_key, True, 3600)  
        
        from blog.models import ArticlePage
        with transaction.atomic():
            ArticlePage.objects.filter(pk=page_id).update(
                view_count=models.F('view_count') + 1
            )
        
        logger.info(f"View count incremented for page {page_id} from IP {ip_address}")
        return True
        
    except Exception as exc:
        logger.error(f"Error incrementing view count: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@shared_task
def update_trending_articles():
    try:
        from blog.models import ArticlePage
        from django.db.models import F, Count, Q
        from django.utils import timezone
        
        last_24h = timezone.now() - timedelta(hours=24)
        
        articles = ArticlePage.objects.live().public()
        
        for article in articles:
            recent_views_key = f"recent_views:{article.id}"
            recent_views = cache.get(recent_views_key, 0)
            
            days_old = (timezone.now() - (article.first_published_at or timezone.now())).days or 1
            trending_score = recent_views / max(days_old, 1)
            
            cache.set(f"trending_score:{article.id}", trending_score, 3600)
        
        logger.info("Updated trending articles successfully")
        
    except Exception as exc:
        logger.error(f"Error updating trending articles: {exc}")


@shared_task
def cleanup_view_tracking():
    try:
        logger.info("Cleaned up view tracking data")
        
    except Exception as exc:
        logger.error(f"Error cleaning up view tracking data: {exc}")


@shared_task
def generate_analytics_summary():
    try:
        from blog.models import ArticlePage, Category
        from django.db.models import Sum, Avg, Count, Q
        from django.utils import timezone
        from datetime import date
        
        today = date.today()
        
        stats = {
            'date': today.isoformat(),
            'total_articles': ArticlePage.objects.live().count(),
            'total_views': ArticlePage.objects.aggregate(
                total=Sum('view_count')
            )['total'] or 0,
            'avg_views_per_article': ArticlePage.objects.aggregate(
                avg=Avg('view_count')
            )['avg'] or 0,
            'articles_by_category': list(
                Category.objects.annotate(
                    article_count=Count('articles', filter=Q(articles__live=True))
                ).values('name', 'article_count')
            )
        }
        
        cache_key = f"daily_stats:{today.isoformat()}"
        cache.set(cache_key, stats, 86400 * 7)  
        
        logger.info(f"Generated analytics summary for {today}")
        return stats
        
    except Exception as exc:
        logger.error(f"Error generating analytics summary: {exc}")

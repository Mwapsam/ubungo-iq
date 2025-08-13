from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from wagtail.images.models import Image
from django.core.cache import cache

from blog.models import ArticlePage, Category
from blog.tasks import convert_image_to_avif


@receiver(post_save, sender=Image)
def image_post_save(sender, instance, created, **kwargs):
    if created:
        convert_image_to_avif.delay(instance.id)


@receiver([post_save, post_delete], sender=ArticlePage)
@receiver([post_save, post_delete], sender=Category)
def invalidate_article_caches(sender, instance, **kwargs):
    cache_keys = [
        "featured_articles",
        "categories_with_counts",
    ]
    common_limits = [5, 10, 20]
    for limit in common_limits:
        cache_keys.append(f"popular_articles_{limit}")
        cache_keys.append(f"recent_articles_{limit}")

    if sender == Category:
        cache_keys.append(f"category_articles_{instance.slug}_all")
        for limit in common_limits:
            cache_keys.append(f"category_articles_{instance.slug}_{limit}")
    elif sender == ArticlePage and instance.category:
        cache_keys.append(f"category_articles_{instance.category.slug}_all")
        for limit in common_limits:
            cache_keys.append(f"category_articles_{instance.category.slug}_{limit}")

    for key in cache_keys:
        cache.delete(key)

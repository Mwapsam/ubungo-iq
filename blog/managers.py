from django.db import models
from django.core.cache import cache
from wagtail.models import PageManager


class OptimizedArticleManager(PageManager):
    def get_queryset(self):
        return super().get_queryset().select_related(
            'category', 'content_type'
        ).prefetch_related(
            'tags'
        )
    
    def published(self):
        return self.get_queryset().live().public()
    
    def featured(self):
        cache_key = "featured_articles"
        featured = cache.get(cache_key)
        
        if featured is None:
            featured = list(
                self.published()
                .filter(featured=True)
                .order_by('-first_published_at')[:5]
            )
            cache.set(cache_key, featured, 900)  
        
        return featured
    
    def popular(self, limit=10):
        cache_key = f"popular_articles_{limit}"
        popular = cache.get(cache_key)
        
        if popular is None:
            popular = list(
                self.published()
                .order_by('-view_count', '-first_published_at')[:limit]
            )
            cache.set(cache_key, popular, 1800)  
            
        return popular
    
    def recent(self, limit=10):
        cache_key = f"recent_articles_{limit}"
        recent = cache.get(cache_key)
        
        if recent is None:
            recent = list(
                self.published()
                .order_by('-first_published_at')[:limit]
            )
            cache.set(cache_key, recent, 600)  
            
        return recent
    
    def by_category(self, category_slug, limit=None):
        cache_key = f"category_articles_{category_slug}_{limit or 'all'}"
        articles = cache.get(cache_key)
        
        if articles is None:
            queryset = self.published().filter(category__slug=category_slug)
            if limit:
                queryset = queryset[:limit]
            articles = list(queryset)
            cache.set(cache_key, articles, 900)  
            
        return articles


class CategoryManager(models.Manager):
    def with_article_counts(self):
        cache_key = "categories_with_counts"
        categories = cache.get(cache_key)
        print(f"Cache get: {categories}")  
        if categories is None:
            from django.db.models import Count, Q
            categories = list(
                self.annotate(
                    article_count=Count(
                        'articles',
                        filter=Q(articles__live=True)
                    )
                ).filter(article_count__gt=0)
                .order_by('name')
            )
            cache.set(cache_key, categories, 1800)
            print(f"Cache set: {categories}")  
        return categories
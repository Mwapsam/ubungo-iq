from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.template.response import TemplateResponse
from django.db.models import Q, Count, F
from datetime import datetime, timedelta
from django.utils import timezone

from blog.models import ArticlePage, Category


@require_http_methods(["GET"])
@cache_page(60 * 5)  # Cache for 5 minutes
def featured_article_ajax(request):
    """AJAX endpoint for featured article section."""
    featured_article = ArticlePage.objects.live().filter(featured=True).first()
    if not featured_article:
        featured_article = ArticlePage.objects.live().first()
    
    if not featured_article:
        return JsonResponse({'error': 'No articles found'}, status=404)
    
    context = {
        'featured_article': featured_article,
        'block_title': request.GET.get('title', 'Featured Article'),
        'show_title': request.GET.get('show_title', 'true').lower() == 'true'
    }
    
    return TemplateResponse(request, 'home/ajax/featured_article.html', context)


@require_http_methods(["GET"])
@cache_page(60 * 5)
def latest_articles_ajax(request):
    """AJAX endpoint for latest articles section."""
    try:
        limit = min(int(request.GET.get('count', 6)), 12)
    except (ValueError, TypeError):
        limit = 6
    
    articles = ArticlePage.objects.live().order_by('-first_published_at')[:limit]
    
    context = {
        'articles': articles,
        'block_title': request.GET.get('title', 'Latest Articles'),
        'show_title': request.GET.get('show_title', 'true').lower() == 'true'
    }
    
    return TemplateResponse(request, 'home/ajax/latest_articles.html', context)


@require_http_methods(["GET"])
@cache_page(60 * 15)  # Cache for 15 minutes
def popular_articles_ajax(request):
    """AJAX endpoint for popular articles section."""
    try:
        limit = min(int(request.GET.get('count', 6)), 12)
    except (ValueError, TypeError):
        limit = 6
    
    time_period = request.GET.get('period', 'month')
    
    # Calculate date filter based on time period
    now = timezone.now()
    if time_period == 'week':
        date_filter = now - timedelta(days=7)
        queryset = ArticlePage.objects.live().filter(first_published_at__gte=date_filter)
    elif time_period == 'month':
        date_filter = now - timedelta(days=30)
        queryset = ArticlePage.objects.live().filter(first_published_at__gte=date_filter)
    else:  # all time
        queryset = ArticlePage.objects.live()
    
    # Order by view count and publication date
    articles = queryset.order_by('-view_count', '-first_published_at')[:limit]
    
    context = {
        'articles': articles,
        'block_title': request.GET.get('title', 'Popular Articles'),
        'show_title': request.GET.get('show_title', 'true').lower() == 'true',
        'time_period': time_period
    }
    
    return TemplateResponse(request, 'home/ajax/popular_articles.html', context)


@require_http_methods(["GET"])
@cache_page(60 * 30)  # Cache for 30 minutes
def category_highlight_ajax(request):
    """AJAX endpoint for category highlight section."""
    try:
        limit = min(int(request.GET.get('count', 6)), 8)
    except (ValueError, TypeError):
        limit = 6
    
    # Get categories with article counts
    categories = Category.objects.annotate(
        article_count=Count('articles', filter=Q(articles__live=True))
    ).filter(article_count__gt=0).order_by('-article_count')[:limit]
    
    context = {
        'categories': categories,
        'block_title': request.GET.get('title', 'Explore Categories'),
        'show_title': request.GET.get('show_title', 'true').lower() == 'true'
    }
    
    return TemplateResponse(request, 'home/ajax/category_highlight.html', context)


@require_http_methods(["GET"])
def ad_space_ajax(request):
    """AJAX endpoint for ad space section."""
    # This would typically load ads from a database or ad service
    # For now, we'll return a placeholder
    
    ad_type = request.GET.get('type', 'banner')
    
    context = {
        'ad_type': ad_type,
        'placeholder': True  # Indicates this is a placeholder ad
    }
    
    return TemplateResponse(request, 'home/ajax/ad_space.html', context)


@require_http_methods(["GET"])
def newsletter_signup_ajax(request):
    """AJAX endpoint for newsletter signup section."""
    context = {
        'block_title': request.GET.get('title', 'Stay Updated'),
        'subtitle': request.GET.get('subtitle', 'Get the latest articles delivered to your inbox'),
        'background_color': request.GET.get('bg_color', 'primary')
    }
    
    return TemplateResponse(request, 'home/ajax/newsletter_signup.html', context)


def serialize_article_summary(article):
    """Serialize article for JSON responses."""
    return {
        'id': article.id,
        'title': article.title,
        'slug': article.slug,
        'url': article.get_url(),
        'intro': article.intro,
        'published_at': article.first_published_at.isoformat() if article.first_published_at else None,
        'formatted_date': article.first_published_at.strftime('%b %d, %Y') if article.first_published_at else '',
        'category': {
            'name': article.category.name if article.category else 'Uncategorized',
            'slug': article.category.slug if article.category else 'uncategorized',
            'color': article.category.color if article.category else '#64748b',
        } if article.category else None,
        'featured_image_url': article.featured_image.get_rendition('width-400|height-250').url if article.featured_image else None,
        'reading_time': article.reading_time_minutes if hasattr(article, 'reading_time_minutes') else 5,
        'view_count': article.view_count,
        'featured': article.featured,
    }
# blog/features.py
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.syndication.views import Feed
from django.urls import reverse
from datetime import datetime, timedelta

from blog.models import ArticlePage, Category
from blog.analytics import analytics


class BlogFeed(Feed):
    """RSS feed for blog articles."""
    
    title = "Ubongo IQ Blog"
    link = "/blog/"
    description = "Latest articles from Ubongo IQ - insights on technology, development, and innovation"
    feed_type = "application/rss+xml"
    
    def items(self):
        return ArticlePage.objects.live().public().order_by('-first_published_at')[:20]
    
    def item_title(self, item):
        return item.title
    
    def item_description(self, item):
        return item.intro or ""
    
    def item_link(self, item):
        return item.get_url()
    
    def item_pubdate(self, item):
        return item.first_published_at
    
    def item_author_name(self, item):
        return "Ubongo IQ Team"
    
    def item_categories(self, item):
        categories = []
        if item.category:
            categories.append(item.category.name)
        categories.extend([tag.name for tag in item.tags.all()])
        return categories


class CategoryFeed(Feed):
    """RSS feed for specific category."""
    
    def get_object(self, request, category_slug):
        return get_object_or_404(Category, slug=category_slug)
    
    def title(self, obj):
        return f"Ubongo IQ - {obj.name}"
    
    def link(self, obj):
        return f"/blog/category/{obj.slug}/"
    
    def description(self, obj):
        return obj.description or f"Latest {obj.name} articles from Ubongo IQ"
    
    def items(self, obj):
        return ArticlePage.objects.live().public().filter(
            category=obj
        ).order_by('-first_published_at')[:20]
    
    def item_title(self, item):
        return item.title
    
    def item_description(self, item):
        return item.intro or ""
    
    def item_link(self, item):
        return item.get_url()
    
    def item_pubdate(self, item):
        return item.first_published_at


@require_http_methods(["GET"])
@cache_page(60 * 30)  # Cache for 30 minutes
def category_page(request, category_slug):
    """Enhanced category page with articles and metadata."""
    category = get_object_or_404(Category, slug=category_slug)
    
    # Track analytics
    analytics.track_page_view(request, category.id, 'category')
    
    # Get articles for this category
    articles = ArticlePage.objects.live().public().filter(
        category=category
    ).select_related('category').prefetch_related('tags')
    
    # Apply additional filters if any
    search = request.GET.get('search', '').strip()
    if search:
        articles = articles.filter(
            Q(title__icontains=search) |
            Q(intro__icontains=search) |
            Q(body__icontains=search)
        )
        analytics.track_search(request, search, articles.count())
    
    # Sorting
    sort = request.GET.get('sort', 'latest')
    if sort == 'popular':
        articles = articles.order_by('-view_count', '-first_published_at')
    elif sort == 'oldest':
        articles = articles.order_by('first_published_at')
    else:
        articles = articles.order_by('-first_published_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get related categories
    related_categories = Category.objects.exclude(id=category.id).annotate(
        article_count=Count('articles', filter=Q(articles__live=True))
    ).filter(article_count__gt=0)[:5]
    
    context = {
        'category': category,
        'articles': page_obj,
        'paginator': paginator,
        'related_categories': related_categories,
        'search_query': search,
        'current_sort': sort,
        'total_articles': paginator.count,
    }
    
    return TemplateResponse(request, 'blog/category_detail.html', context)


@require_http_methods(["GET"])
def get_related_articles(request, article_id):
    """Get related articles for the current article."""
    try:
        article = ArticlePage.objects.get(id=article_id)
    except ArticlePage.DoesNotExist:
        return JsonResponse({'error': 'Article not found'}, status=404)
    
    # Cache key for related articles
    cache_key = f"related_articles_{article_id}"
    related_articles = cache.get(cache_key)
    
    if related_articles is None:
        # Find related articles based on category and tags
        related = ArticlePage.objects.live().public().exclude(id=article_id)
        
        # Same category articles
        if article.category:
            related = related.filter(category=article.category)
        
        # Articles with similar tags
        if article.tags.exists():
            tag_names = list(article.tags.values_list('name', flat=True))
            related = related.filter(tags__name__in=tag_names).distinct()
            
            # Order by number of matching tags
            related = related.annotate(
                tag_matches=Count('tags', filter=Q(tags__name__in=tag_names))
            ).order_by('-tag_matches', '-first_published_at')
        else:
            related = related.order_by('-first_published_at')
        
        # Get top 6 related articles
        related_articles = list(related[:6])
        cache.set(cache_key, related_articles, 1800)  # Cache for 30 minutes
    
    # Serialize articles
    articles_data = []
    for related_article in related_articles:
        articles_data.append({
            'id': related_article.id,
            'title': related_article.title,
            'slug': related_article.slug,
            'url': related_article.get_url(),
            'intro': related_article.intro,
            'published_at': related_article.first_published_at.isoformat() if related_article.first_published_at else None,
            'category': {
                'name': related_article.category.name if related_article.category else None,
                'slug': related_article.category.slug if related_article.category else None,
                'color': related_article.category.color if related_article.category else None,
            },
            'featured_image': {
                'url': related_article.featured_image.get_rendition('width-400|height-250').url if related_article.featured_image else None,
                'alt': related_article.featured_image.title if related_article.featured_image else '',
            },
            'reading_time': getattr(related_article, 'reading_time_minutes', 5),
            'view_count': related_article.view_count,
        })
    
    return JsonResponse({'related_articles': articles_data})


@require_http_methods(["GET"])
@cache_page(60 * 60)  # Cache for 1 hour
def popular_articles(request):
    """Get popular articles for sidebar/widgets."""
    timeframe = request.GET.get('timeframe', 'all_time')  # all_time, week, month
    limit = min(int(request.GET.get('limit', 5)), 20)
    
    cache_key = f"popular_articles_{timeframe}_{limit}"
    popular = cache.get(cache_key)
    
    if popular is None:
        articles = ArticlePage.objects.live().public()
        
        if timeframe == 'week':
            week_ago = timezone.now() - timedelta(days=7)
            # In a real implementation, you'd have a separate view tracking table
            # For now, use publication date as proxy
            articles = articles.filter(first_published_at__gte=week_ago)
        elif timeframe == 'month':
            month_ago = timezone.now() - timedelta(days=30)
            articles = articles.filter(first_published_at__gte=month_ago)
        
        popular = list(
            articles.order_by('-view_count', '-first_published_at')[:limit]
        )
        cache.set(cache_key, popular, 1800)  # Cache for 30 minutes
    
    articles_data = []
    for article in popular:
        articles_data.append({
            'title': article.title,
            'url': article.get_url(),
            'view_count': article.view_count,
            'published_at': article.first_published_at.isoformat() if article.first_published_at else None,
            'category': {
                'name': article.category.name if article.category else None,
                'color': article.category.color if article.category else None,
            }
        })
    
    return JsonResponse({'articles': articles_data})


@require_http_methods(["GET"])
def tag_articles(request, tag_slug):
    """Get articles by tag."""
    from taggit.models import Tag
    
    try:
        tag = Tag.objects.get(slug=tag_slug)
    except Tag.DoesNotExist:
        return JsonResponse({'error': 'Tag not found'}, status=404)
    
    # Track analytics
    analytics.track_page_view(request, tag.id, 'tag')
    
    articles = ArticlePage.objects.live().public().filter(
        tags__slug=tag_slug
    ).distinct().order_by('-first_published_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Serialize articles
    articles_data = []
    for article in page_obj:
        articles_data.append({
            'id': article.id,
            'title': article.title,
            'url': article.get_url(),
            'intro': article.intro,
            'published_at': article.first_published_at.isoformat() if article.first_published_at else None,
            'category': {
                'name': article.category.name if article.category else None,
                'slug': article.category.slug if article.category else None,
                'color': article.category.color if article.category else None,
            },
            'view_count': article.view_count,
        })
    
    return JsonResponse({
        'tag': {
            'name': tag.name,
            'slug': tag.slug,
        },
        'articles': articles_data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_count': paginator.count,
        }
    })


@require_http_methods(["POST"])
def share_article(request):
    """Track article sharing."""
    import json
    
    try:
        data = json.loads(request.body)
        article_id = data.get('article_id')
        platform = data.get('platform')  # twitter, facebook, linkedin, etc.
        
        if not article_id or not platform:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Track the share event
        analytics.track_user_action(
            request, 
            'share_article', 
            target=article_id,
            metadata={'platform': platform}
        )
        
        # Increment share count in cache
        share_key = f"article_shares_{article_id}_{platform}"
        current_shares = cache.get(share_key, 0)
        cache.set(share_key, current_shares + 1, 86400)  # 24 hours
        
        return JsonResponse({'success': True, 'message': 'Share tracked'})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Server error'}, status=500)


def generate_sitemap_xml(request):
    """Generate sitemap.xml for SEO."""
    from django.template.loader import render_to_string
    
    # Get all live pages
    pages = ArticlePage.objects.live().public().order_by('-last_published_at')
    categories = Category.objects.annotate(
        article_count=Count('articles', filter=Q(articles__live=True))
    ).filter(article_count__gt=0)
    
    context = {
        'pages': pages,
        'categories': categories,
        'request': request,
    }
    
    xml_content = render_to_string('blog/sitemap.xml', context)
    return HttpResponse(xml_content, content_type='application/xml')


def robots_txt(request):
    """Generate robots.txt file."""
    from blog.seo import generate_robots_txt
    
    content = generate_robots_txt()
    return HttpResponse(content, content_type='text/plain')


@require_http_methods(["GET"])
@cache_page(60 * 15)  # Cache for 15 minutes
def archive_view(request):
    """Archive page showing articles by date."""
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    articles = ArticlePage.objects.live().public()
    
    if year:
        articles = articles.filter(first_published_at__year=year)
        if month:
            articles = articles.filter(first_published_at__month=month)
    
    articles = articles.order_by('-first_published_at')
    
    # Group articles by month for archive view
    from itertools import groupby
    from django.utils.dates import MONTHS
    
    grouped_articles = {}
    for key, group in groupby(articles, key=lambda x: (x.first_published_at.year, x.first_published_at.month) if x.first_published_at else (None, None)):
        if key[0] and key[1]:
            month_name = MONTHS[key[1]]
            grouped_articles[f"{month_name} {key[0]}"] = list(group)
    
    context = {
        'grouped_articles': grouped_articles,
        'current_year': year,
        'current_month': month,
        'available_years': articles.dates('first_published_at', 'year', order='DESC'),
    }
    
    return TemplateResponse(request, 'blog/archive.html', context)
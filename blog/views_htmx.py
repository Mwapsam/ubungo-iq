# blog/views_htmx.py
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from blog.models import ArticlePage, Category
from blog.analytics import analytics


@require_http_methods(["GET"])
@cache_page(60 * 5)  # Cache for 5 minutes
def load_more_articles(request):
    """Load articles with HTMX pagination and filtering."""
    page_num = request.GET.get('page', 1)
    category = request.GET.get('category', '').strip()
    search = request.GET.get('search', '').strip()
    sort = request.GET.get('sort', 'latest').strip()
    per_page = min(int(request.GET.get('per_page', 12)), 50)
    featured_only = request.GET.get('featured') == 'true'
    
    # Base queryset with optimizations
    articles = ArticlePage.objects.live().public().select_related(
        'category'
    ).prefetch_related('tags')
    
    # Apply featured filter
    if featured_only:
        articles = articles.filter(featured=True)
        per_page = min(per_page, 6)  # Limit featured articles
    
    # Apply category filter
    if category and category != 'all':
        articles = articles.filter(category__slug=category)
    
    # Apply search filter
    if search:
        articles = articles.filter(
            Q(title__icontains=search) |
            Q(intro__icontains=search) |
            Q(body__icontains=search) |
            Q(tags__name__icontains=search)
        ).distinct()
        
        # Track search (only if session is available)
        try:
            analytics.track_search(request, search, articles.count())
        except (AttributeError, KeyError):
            # Session not available, skip analytics
            pass
    
    # Apply sorting
    if sort == 'popular':
        articles = articles.order_by('-view_count', '-first_published_at')
    elif sort == 'oldest':
        articles = articles.order_by('first_published_at')
    else:  # latest
        articles = articles.order_by('-first_published_at')
    
    # Paginate
    paginator = Paginator(articles, per_page)
    
    try:
        page_obj = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        if request.headers.get('HX-Request'):
            return JsonResponse({'articles': [], 'has_more': False})
        page_obj = paginator.page(1)
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        # Return HTML for HTMX
        if featured_only:
            template = 'blog/partials/featured_articles.html'
        else:
            template = 'blog/partials/article_grid.html'
            
        html = render_to_string(template, {
            'articles': page_obj,
            'request': request
        })
        
        response = TemplateResponse(request, template, {
            'articles': page_obj,
        })
        
        # Add HX-Trigger header for JavaScript events
        if page_obj.has_next():
            response['HX-Trigger'] = 'articlesLoaded'
        else:
            response['HX-Trigger'] = 'allArticlesLoaded'
            
        return response
    
    # Return JSON for regular AJAX requests
    articles_data = []
    for article in page_obj:
        articles_data.append({
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
            },
            'tags': [
                {'name': tag.name, 'slug': tag.slug} 
                for tag in article.tags.all()
            ],
            'featured_image': {
                'url': article.featured_image.get_rendition('width-600|height-400').url if article.featured_image else None,
                'alt': article.featured_image.title if article.featured_image else '',
            },
            'reading_time': getattr(article, 'reading_time_minutes', 5),
            'view_count': article.view_count,
            'featured': article.featured,
        })
    
    return JsonResponse({
        'articles': articles_data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_count': paginator.count,
        },
        'filters': {
            'search': search,
            'category': category,
            'sort': sort,
        }
    })


@require_http_methods(["GET"])
def get_categories_api(request):
    """Get categories with article counts for dropdowns."""
    from django.core.cache import cache
    
    # Create different cache keys for HTMX vs regular requests
    is_htmx = bool(request.headers.get('HX-Request'))
    cache_key = f"categories_api_{is_htmx}"
    
    # Try to get from cache first
    cached_content = cache.get(cache_key)
    if cached_content:
        if is_htmx:
            from django.http import HttpResponse
            return HttpResponse(cached_content, content_type='text/html')
        else:
            return cached_content
    
    categories_with_counts = Category.objects.annotate(
        article_count=Count('articles', filter=Q(articles__live=True))
    ).filter(article_count__gt=0).order_by('name')
    
    if is_htmx:
        # Return HTML for HTMX - render the template to string for caching
        html_content = render_to_string('blog/partials/category_dropdown.html', {
            'categories': categories_with_counts
        })
        # Cache the HTML content for 15 minutes
        cache.set(cache_key, html_content, 60 * 15)
        
        from django.http import HttpResponse
        return HttpResponse(html_content, content_type='text/html')
    
    # Return JSON
    categories_data = []
    for category in categories_with_counts:
        categories_data.append({
            'name': category.name,
            'slug': category.slug,
            'color': category.color,
            'count': category.article_count,
            'description': category.description,
        })
    
    json_data = {'categories': categories_data}
    # Cache the JSON data for 15 minutes
    cache.set(cache_key, JsonResponse(json_data), 60 * 15)
    return JsonResponse(json_data)


@require_http_methods(["GET"])
def search_articles(request):
    """Search articles with autocomplete suggestions."""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'articles': [], 'suggestions': []})
    
    # Search articles
    articles = ArticlePage.objects.live().public().filter(
        Q(title__icontains=query) |
        Q(intro__icontains=query) |
        Q(body__icontains=query)
    ).select_related('category')[:10]
    
    # Get suggestions (similar titles)
    suggestions = ArticlePage.objects.live().public().filter(
        title__icontains=query
    ).values_list('title', flat=True)[:5]
    
    # Track search (only if session is available)
    try:
        analytics.track_search(request, query, articles.count())
    except (AttributeError, KeyError):
        # Session not available, skip analytics
        pass
    
    if request.headers.get('HX-Request'):
        # Return HTML for HTMX
        return TemplateResponse(request, 'blog/partials/search_results.html', {
            'articles': articles,
            'query': query,
            'suggestions': suggestions
        })
    
    # Serialize articles for JSON
    articles_data = []
    for article in articles:
        articles_data.append({
            'title': article.title,
            'url': article.get_url(),
            'intro': article.intro[:150] + '...' if len(article.intro) > 150 else article.intro,
            'category': article.category.name if article.category else None,
            'formatted_date': article.first_published_at.strftime('%b %d, %Y') if article.first_published_at else '',
        })
    
    return JsonResponse({
        'articles': articles_data,
        'suggestions': list(suggestions),
        'query': query
    })


@require_http_methods(["GET"])
def get_related_articles(request, article_id):
    """Get related articles for the given article."""
    try:
        article = ArticlePage.objects.get(id=article_id)
    except ArticlePage.DoesNotExist:
        return JsonResponse({'error': 'Article not found'}, status=404)
    
    # Get related articles using the template tag logic
    from blog.templatetags.seo_tags import get_related_articles
    related_articles = get_related_articles(article, limit=6)
    
    if request.headers.get('HX-Request'):
        # Return HTML for HTMX
        return TemplateResponse(request, 'blog/partials/related_articles.html', {
            'related_articles': related_articles
        })
    
    # Serialize for JSON
    articles_data = []
    for related in related_articles:
        articles_data.append({
            'id': related.id,
            'title': related.title,
            'url': related.get_url(),
            'intro': related.intro,
            'category': {
                'name': related.category.name if related.category else None,
                'slug': related.category.slug if related.category else None,
                'color': related.category.color if related.category else None,
            },
            'featured_image': {
                'url': related.featured_image.get_rendition('width-400|height-250').url if related.featured_image else None,
                'alt': related.featured_image.title if related.featured_image else '',
            },
            'reading_time': getattr(related, 'reading_time_minutes', 5),
            'view_count': related.view_count,
        })
    
    return JsonResponse({'related_articles': articles_data})


@require_http_methods(["POST"])
def track_view(request):
    """Track page view via AJAX."""
    import json
    
    try:
        data = json.loads(request.body)
        page_id = data.get('page_id')
        
        if page_id:
            # Track view using analytics
            analytics.track_page_view(request, page_id, 'article')
            
            # Queue async view count increment
            from blog.tasks import increment_view_count_async
            ip_address = analytics.get_client_ip(request)
            increment_view_count_async.delay(page_id, ip_address)
        
        return JsonResponse({'success': True})
        
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request'}, status=400)


@require_http_methods(["POST"])
def submit_comment(request):
    """Mock comment submission (replace with real implementation)."""
    import json
    
    try:
        data = request.POST
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        comment = data.get('comment', '').strip()
        article_id = data.get('article_id')
        
        if not all([name, email, comment, article_id]):
            return JsonResponse({'error': 'All fields are required'}, status=400)
        
        # Track comment submission
        analytics.track_user_action(
            request, 
            'submit_comment', 
            target=article_id,
            metadata={'name': name}
        )
        
        # Return success response with mock comment HTML
        comment_html = render_to_string('blog/partials/comment.html', {
            'comment': {
                'name': name,
                'content': comment,
                'created_at': 'Just now',
                'initials': ''.join([word[0].upper() for word in name.split()[:2]])
            }
        })
        
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'blog/partials/comment.html', {
                'comment': {
                    'name': name,
                    'content': comment,
                    'created_at': 'Just now',
                    'initials': ''.join([word[0].upper() for word in name.split()[:2]])
                }
            })
        
        return JsonResponse({
            'success': True,
            'message': 'Comment submitted successfully',
            'html': comment_html
        })
        
    except Exception as e:
        return JsonResponse({'error': 'Server error'}, status=500)


@require_http_methods(["GET"])
def infinite_scroll(request):
    """Infinite scroll implementation for article lists."""
    page_num = int(request.GET.get('page', 1))
    category = request.GET.get('category', '')
    
    articles = ArticlePage.objects.live().public()
    
    if category:
        articles = articles.filter(category__slug=category)
    
    articles = articles.order_by('-first_published_at')
    
    paginator = Paginator(articles, 12)
    
    try:
        page_obj = paginator.page(page_num)
    except EmptyPage:
        return JsonResponse({'articles': [], 'has_more': False})
    
    if request.headers.get('HX-Request'):
        return TemplateResponse(request, 'blog/partials/infinite_scroll.html', {
            'articles': page_obj,
            'page_obj': page_obj
        })
    
    return JsonResponse({
        'has_more': page_obj.has_next(),
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None
    })
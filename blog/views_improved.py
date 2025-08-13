# blog/views_improved.py
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, F
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from wagtail.models import Page
from wagtail.contrib.search_promotions.models import Query


from blog.models import ArticlePage, Category
import logging

logger = logging.getLogger(__name__)


class BlogViewMixin:
    def get_base_queryset(self):
        return ArticlePage.objects.live().public().select_related(
            'category'
        ).prefetch_related(
            'tags'
        )


    def apply_filters(self, queryset, request):
        category = request.GET.get("category", "").strip()
        if category and category != "all":
            queryset = queryset.filter(category__slug=category)

        search_query = request.GET.get("search", "").strip()
        if search_query:
            Query.get(search_query).add_hit()

            try:
                queryset = queryset.search(search_query, operator="and")
            except Exception as e:  
                queryset = queryset.filter(
                    Q(title__icontains=search_query)
                    | Q(intro__icontains=search_query)
                    | Q(body__icontains=search_query)
                    | Q(tags__name__icontains=search_query)
                ).distinct()

        tag = request.GET.get("tag", "").strip()
        if tag:
            queryset = queryset.filter(tags__slug=tag)

        featured = request.GET.get("featured")
        if featured == "true":
            queryset = queryset.filter(featured=True)

        return queryset, search_query

    def apply_sorting(self, queryset, request):
        sort = request.GET.get('sort', 'latest').strip()

        sort_options = {
            'latest': '-first_published_at',
            'oldest': 'first_published_at', 
            'popular': ['-view_count', '-first_published_at'],
            'title': 'title',
            'reading_time': 'body',  
        }

        if sort in sort_options:
            order_by = sort_options[sort]
            if isinstance(order_by, list):
                queryset = queryset.order_by(*order_by)
            else:
                queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by('-first_published_at')

        return queryset

    def get_pagination_data(self, queryset, page_num, per_page=12):
        paginator = Paginator(queryset, per_page)

        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        return page_obj, paginator


@require_http_methods(["GET"])
@vary_on_headers('Accept')
@cache_page(60 * 5)  
def enhanced_article_list(request):
    view_mixin = BlogViewMixin()
    
    queryset = view_mixin.get_base_queryset()
    
    queryset, search_query = view_mixin.apply_filters(queryset, request)
    
    queryset = view_mixin.apply_sorting(queryset, request)
    
    page_num = request.GET.get('page', 1)
    per_page = min(int(request.GET.get('per_page', 12)), 50)  
    
    page_obj, paginator = view_mixin.get_pagination_data(queryset, page_num, per_page)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'articles': [serialize_article(article) for article in page_obj],
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'total_count': paginator.count,
            },
            'filters': {
                'search': search_query,
                'category': request.GET.get('category', ''),
                'tag': request.GET.get('tag', ''),
                'sort': request.GET.get('sort', 'latest'),
            }
        })
    
    context = {
        'articles': page_obj,
        'paginator': paginator,
        'search_query': search_query,
        'current_filters': {
            'category': request.GET.get('category', ''),
            'tag': request.GET.get('tag', ''),
            'sort': request.GET.get('sort', 'latest'),
        }
    }
    
    return TemplateResponse(request, 'blog/enhanced_article_list.html', context)


def serialize_article(article):
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
        },
        'tags': [
            {'name': tag.name, 'slug': tag.slug} 
            for tag in article.tags.all()
        ],
        'featured_image': {
            'url': article.featured_image.get_rendition('width-600|height-400').url if article.featured_image else None,
            'alt': article.featured_image.title if article.featured_image else '',
        },
        'reading_time': article.reading_time_minutes if hasattr(article, 'reading_time_minutes') else 5,
        'view_count': article.view_count,
        'featured': article.featured,
    }


@require_http_methods(["GET"])
@cache_page(60 * 15) 
def category_detail(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    
    view_mixin = BlogViewMixin()
    queryset = view_mixin.get_base_queryset().filter(category=category)
    
    request_copy = request.GET.copy()
    request_copy.pop('category', None) 
    
    temp_request = type('', (), {'GET': request_copy})()
    queryset, search_query = view_mixin.apply_filters(queryset, temp_request)
    queryset = view_mixin.apply_sorting(queryset, temp_request)
    
    page_num = request.GET.get('page', 1)
    page_obj, paginator = view_mixin.get_pagination_data(queryset, page_num)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'articles': [serialize_article(article) for article in page_obj],
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'total_count': paginator.count,
            },
            'category': {
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'color': category.color,
            }
        })
    
    context = {
        'category': category,
        'articles': page_obj,
        'paginator': paginator,
        'search_query': search_query,
    }
    
    return TemplateResponse(request, 'blog/category_detail_modern.html', context)


@require_http_methods(["GET"])
def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    cache_key = f"search_suggestions_{query[:20]}"
    suggestions = cache.get(cache_key)
    
    if suggestions is None:
        title_matches = ArticlePage.objects.live().public().filter(
            title__icontains=query
        ).values_list('title', flat=True)[:5]
        
        from taggit.models import Tag
        tag_matches = Tag.objects.filter(
            name__icontains=query
        ).values_list('name', flat=True)[:3]
        
        suggestions = {
            'articles': list(title_matches),
            'tags': list(tag_matches),
        }
        
        cache.set(cache_key, suggestions, 300) 
    
    return JsonResponse({'suggestions': suggestions})


@require_http_methods(["GET"]) 
def get_filter_options(request):
    """Get available filter options for the frontend."""
    cache_key = "blog_filter_options"
    options = cache.get(cache_key)
    
    if options is None:
        # Get categories with article counts
        categories = Category.objects.annotate(
            article_count=Count('articles', filter=Q(articles__live=True))
        ).filter(article_count__gt=0).values(
            'name', 'slug', 'color', 'article_count'
        )
        
        # Get popular tags
        from taggit.models import Tag
        popular_tags = Tag.objects.annotate(
            usage_count=Count('taggit_taggeditem_items')
        ).filter(usage_count__gt=0).order_by('-usage_count')[:20].values(
            'name', 'slug', 'usage_count'
        )
        
        options = {
            'categories': list(categories),
            'tags': list(popular_tags),
            'sort_options': [
                {'value': 'latest', 'label': 'Latest'},
                {'value': 'oldest', 'label': 'Oldest'},
                {'value': 'popular', 'label': 'Most Popular'},
                {'value': 'title', 'label': 'Title A-Z'},
            ]
        }
        
        cache.set(cache_key, options, 900)  
    
    return JsonResponse(options)

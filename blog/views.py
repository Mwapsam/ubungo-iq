from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from wagtail.models import Page
from blog.models import ArticlePage, Category


@require_http_methods(["GET"])
# @cache_page(60 * 5)  
def load_more_articles(request):
    page = int(request.GET.get("page", 2))
    category = request.GET.get("category", "")
    search = request.GET.get("search", "")
    sort = request.GET.get("sort", "latest")
    per_page = 6

    articles = ArticlePage.objects.live().public()

    if category and category != "all":
        articles = articles.filter(category__slug=category)

    if search:
        articles = articles.filter(
            Q(title__icontains=search)
            | Q(intro__icontains=search)
            | Q(body__icontains=search)
            | Q(tags__name__icontains=search)
        ).distinct()

    if sort == "popular":
        articles = articles.order_by("-view_count", "-published_at")
    elif sort == "oldest":
        articles = articles.order_by("published_at")
    else:  
        articles = articles.order_by("-published_at")

    paginator = Paginator(articles, per_page)

    try:
        page_obj = paginator.page(page)
    except:
        return JsonResponse({"articles": [], "has_more": False})

    articles_data = []
    for article in page_obj:
        article.increment_view_count()

        articles_data.append(
            {
                "title": article.title,
                "url": article.url,
                "intro": article.intro,
                "date": article.published_at.strftime("%Y-%m-%d"),
                "formatted_date": article.published_at.strftime("%b %d, %Y"),
                "category": {
                    "name": (
                        article.category.name if article.category else "Uncategorized"
                    ),
                    "slug": (
                        article.category.slug if article.category else "uncategorized"
                    ),
                    "color": article.category.color if article.category else "#64748b",
                },
                "tags": [
                    {"name": tag.name, "slug": tag.slug} for tag in article.tags.all()
                ],
                "featured_image": (
                    article.featured_image.get_rendition("width-600|height-400").url
                    if article.featured_image
                    else None
                ),
                "reading_time": article.reading_time_minutes,
                "view_count": article.view_count,
                "featured": article.featured,
            }
        )

    return JsonResponse(
        {
            "articles": articles_data,
            "has_more": page_obj.has_next(),
            "total_pages": paginator.num_pages,
            "current_page": page,
        }
    )


@require_http_methods(["GET"])
def get_categories_with_counts(request):
    categories = (
        Category.objects.annotate(
            article_count=Count("articlepage", filter=Q(articlepage__live=True))
        )
        .order_by("name")
    )

    categories_data = [
        {
            "name": cat.name,
            "slug": cat.slug,
            "color": cat.color,
            "count": cat.article_count,
        }
        for cat in categories
    ]

    return JsonResponse({"categories": categories_data})

from django.http import JsonResponse
from blog.models import ArticlePage


def load_more_articles(request):
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        limit = int(request.GET.get("limit", 3))
        offset = int(request.GET.get("offset", 0))

        articles = ArticlePage.objects.live().order_by("-first_published_at")[
            offset : offset + limit
        ]

        data = [
            {
                "title": article.title,
                "url": article.url,
                "intro": article.intro[:100] + "...",
                "date": article.first_published_at.strftime("%Y-%m-%d"),
            }
            for article in articles
        ]
        return JsonResponse({"articles": data})

    return JsonResponse({"error": "Invalid request"}, status=400)

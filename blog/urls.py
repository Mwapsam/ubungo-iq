from django.urls import path

from blog import views, views_htmx, views_improved, views_dashboard
from blog.features import BlogFeed, CategoryFeed

app_name = 'blog'

urlpatterns = [
    # Category pages
    path("categories/", views_improved.categories_page, name="categories_page"),
    path("category/<slug:category_slug>/", views_improved.category_detail, name="category_detail"),
    
    # Tag pages
    path("tag/<slug:tag_slug>/", views_improved.tag_detail, name="tag_detail"),
    
    # HTMX API endpoints
    path("api/load_more_articles/", views_htmx.load_more_articles, name="load_more_articles"),
    path("api/categories/", views_htmx.get_categories_api, name="get_categories"),
    path("api/search/", views_htmx.search_articles, name="search"),
    path("api/articles/<int:article_id>/related/", views_htmx.get_related_articles, name="related_articles"),
    path("api/track-view/", views_htmx.track_view, name="track_view"),
    path("api/comments/", views_htmx.submit_comment, name="submit_comment"),
    path("api/infinite-scroll/", views_htmx.infinite_scroll, name="infinite_scroll"),
    
    # RSS Feeds
    path("feed/", BlogFeed(), name="feed"),
    path("category/<slug:category_slug>/feed/", CategoryFeed(), name="category_feed"),
    
    # Analytics Dashboard
    path("dashboard/", views_dashboard.dashboard_home, name="dashboard"),
    path("api/market-overview/", views_dashboard.api_market_overview, name="api_market_overview"),
    path("api/price-trends/", views_dashboard.api_price_trends, name="api_price_trends"),
    path("api/supplier-distribution/", views_dashboard.api_supplier_distribution, name="api_supplier_distribution"),
    path("api/trending-topics/", views_dashboard.api_trending_topics, name="api_trending_topics"),
    path("api/scraping-health/", views_dashboard.api_scraping_health, name="api_scraping_health"),
    path("api/content-opportunities/", views_dashboard.api_content_opportunities, name="api_content_opportunities"),
    path("api/alerts-summary/", views_dashboard.api_alerts_summary, name="api_alerts_summary"),
    
    # Legacy API (keep for backwards compatibility) - moved to different endpoint
    path("api/legacy/categories/", views.get_categories_with_counts, name="get_categories_legacy"),
]

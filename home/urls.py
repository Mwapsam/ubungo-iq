from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    # AJAX endpoints for dynamic section loading
    path('api/featured-article/', views.featured_article_ajax, name='featured_article_ajax'),
    path('api/latest-articles/', views.latest_articles_ajax, name='latest_articles_ajax'),
    path('api/popular-articles/', views.popular_articles_ajax, name='popular_articles_ajax'),
    path('api/category-highlight/', views.category_highlight_ajax, name='category_highlight_ajax'),
    path('api/ad-space/', views.ad_space_ajax, name='ad_space_ajax'),
    path('api/newsletter-signup/', views.newsletter_signup_ajax, name='newsletter_signup_ajax'),
]
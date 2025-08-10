from django.urls import path

from blog import views

urlpatterns = [
    # path("ajax/load-articles/", views.load_more_articles, name="load_more_articles"),
    path(
        "api/load_more_articles/", views.load_more_articles, name="load_more_articles"
    ),
    path("api/categories/", views.get_categories_with_counts, name="get_categories"),
]

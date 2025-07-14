from django.urls import path

from blog import views

urlpatterns = [
    path("ajax/load-articles/", views.load_more_articles, name="load_more_articles"),
]
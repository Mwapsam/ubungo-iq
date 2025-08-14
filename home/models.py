from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel
from wagtail import blocks
from datetime import datetime, timedelta
from django.utils import timezone

from blog.models import ArticlePage, Category
from .blocks import (
    FeaturedArticleBlock,
    LatestArticlesBlock, 
    PopularArticlesBlock,
    AdSpaceBlock,
    CategoryHighlightBlock,
    NewsletterSignupBlock
)


class HomePage(Page):
    intro = RichTextField(blank=True)
    
    content_sections = StreamField([
        ('featured_article', FeaturedArticleBlock()),
        ('latest_articles', LatestArticlesBlock()),
        ('popular_articles', PopularArticlesBlock()),
        ('ad_space', AdSpaceBlock()),
        ('category_highlight', CategoryHighlightBlock()),
        ('newsletter_signup', NewsletterSignupBlock()),
    ], use_json_field=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("content_sections"),
    ]

    def get_context(self, request):
        context = super().get_context(request)

        # Get featured article (most recent featured or first article)
        featured_article = ArticlePage.objects.live().filter(featured=True).first()
        if not featured_article:
            featured_article = ArticlePage.objects.live().first()
        
        context["featured_article"] = featured_article
        context["articles"] = ArticlePage.objects.live().order_by("-first_published_at")
        context["categories"] = Category.objects.all()

        return context

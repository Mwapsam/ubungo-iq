from django.db import models
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.snippets.models import register_snippet
from wagtail.search import index
from taggit.models import TaggedItemBase
from modelcluster.fields import ParentalKey
from modelcluster.tags import ClusterTaggableManager
from django_extensions.db.fields import AutoSlugField
import readtime

from blog.managers import CategoryManager, OptimizedArticleManager
from blog.seo import ArticleSEOMixin
from utils.generators import slugify_function


@register_snippet
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(
        populate_from="name", slugify_function=slugify_function, unique=True
    )
    color = models.CharField(max_length=7, default="#3b82f6")
    description = models.TextField(blank=True, null=True)

    objects = CategoryManager()

    panels = [FieldPanel("name"), FieldPanel("description"), FieldPanel("color")]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]


class ArticlePageTag(TaggedItemBase):
    content_object = ParentalKey(
        "ArticlePage", related_name="tagged_items", on_delete=models.CASCADE
    )


class BlogIndexPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["blog.ArticlePage"]

    def get_context(self, request):
        context = super().get_context(request)
        context["articles"] = (
            ArticlePage.objects.live()
            .descendant_of(self)
            .order_by("-first_published_at")
        )
        return context


# --- Article Page ---
class ArticlePage(Page, ArticleSEOMixin):
    intro = models.CharField(max_length=250, blank=True)
    body = RichTextField()
    summary = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="articles",
    )
    tags = ClusterTaggableManager(through=ArticlePageTag, blank=True)
    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    published_at = models.DateTimeField(auto_now_add=True)
    view_count = models.PositiveIntegerField(default=0)
    featured = models.BooleanField(default=False) 
    meta_description = models.TextField(blank=True, null=True)

    objects = OptimizedArticleManager()

    content_panels = Page.content_panels + [
        FieldPanel("seo_title"),
        FieldPanel("meta_description"),
        FieldPanel("intro"),
        FieldPanel("body"),
        FieldPanel("summary"),
        FieldPanel("category"),
        FieldPanel("tags"),
        FieldPanel("featured_image"),
        FieldPanel("featured"),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("title"),
        index.SearchField("intro"),
        index.SearchField("body"),
        index.FilterField("category"),
    ]

    parent_page_types = ["blog.BlogIndexPage"]
    subpage_types = []

    def __str__(self):
        return self.title

    @property
    def reading_time(self):
        content = f"{self.intro} {self.body}"
        return readtime.of_text(content)

    @property
    def reading_time_minutes(self):
        rt = self.reading_time
        return max(1, rt.minutes)

    def increment_view_count(self):
        ArticlePage.objects.filter(pk=self.pk).update(
            view_count=models.F("view_count") + 1
        )


# Import AI content generation models
from .models_ai import ContentGenerationRequest, AIContentMetrics

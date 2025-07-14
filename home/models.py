from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel

from blog.models import ArticlePage, Category  


class HomePage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    def get_context(self, request):
        context = super().get_context(request)

        context["articles"] = ArticlePage.objects.live().order_by(
            "-first_published_at"
        )
        context["categories"] = Category.objects.all()

        return context

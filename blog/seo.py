from django.utils.html import strip_tags
from wagtail.contrib.sitemaps import Sitemap
from wagtail.models import Page
import re


class SEOMixin:
    def get_meta_title(self):
        if hasattr(self, 'seo_title') and self.seo_title:
            return self.seo_title
        return f"{self.title} | Ubongo IQ"

    def get_meta_description(self):
        if hasattr(self, 'meta_description') and self.meta_description:
            return self.meta_description

        if hasattr(self, 'intro') and self.intro:
            return self.truncate_description(self.intro)

        if hasattr(self, 'body') and self.body:
            clean_body = strip_tags(str(self.body))
            return self.truncate_description(clean_body)

        return "Discover insightful articles on technology, development, and innovation at Ubongo IQ."

    def truncate_description(self, text, max_length=155):
        text = re.sub(r'\s+', ' ', text.strip())
        if len(text) <= max_length:
            return text

        truncated = text[:max_length].rsplit(' ', 1)[0]
        return f"{truncated}..."


    def get_canonical_url(self):
        from wagtail.models import Site

        try:
            site = Site.objects.get(is_default_site=True)
        except Site.DoesNotExist:
            site = Site.objects.first()

        if not site:
            return f"https://ubongoiq.com{self.get_url() or '/'}"

        protocol = "https"
        port = "" if site.port in [80, 443] else f":{site.port}"
        url_path = self.get_url() or f"/{self.slug}/"

        return f"{protocol}://{site.hostname}{port}{url_path}"

    def get_structured_data(self):
        return {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": self.get_meta_title(),
            "description": self.get_meta_description(),
            "url": self.get_canonical_url(),
        }

    def get_open_graph_data(self):
        og_data = {
            'title': self.get_meta_title(),
            'description': self.get_meta_description(),
            'url': self.get_canonical_url(),
            'type': 'website',
            'site_name': 'Ubongo IQ',
        }

        if hasattr(self, 'featured_image') and self.featured_image:
            try:
                rendition = self.featured_image.get_rendition('width-1200|height-630')
                og_data['image'] = rendition.url
                og_data['image:width'] = '1200'
                og_data['image:height'] = '630'
            except Exception:
                pass

        return og_data

    def get_twitter_card_data(self):
        twitter_data = {
            'card': 'summary_large_image',
            'title': self.get_meta_title(),
            'description': self.get_meta_description(),
        }

        if hasattr(self, 'featured_image') and self.featured_image:
            try:
                rendition = self.featured_image.get_rendition('width-1200|height-600')
                twitter_data['image'] = rendition.url
            except Exception:
                pass

        return twitter_data


class ArticleSEOMixin(SEOMixin):
    def get_canonical_url(self):
        from django.contrib.sites.models import Site

        site = Site.objects.get_current()
        url_path = self.get_url()
        if url_path is None:
            url_path = self.url_path or f"/{self.slug}/"
        return f"https://{site.domain}{url_path}"

    def get_structured_data(self):
        data = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": self.get_meta_title(),
            "description": self.get_meta_description(),
            "url": self.get_canonical_url(),
            "datePublished": self.first_published_at.isoformat() if self.first_published_at else None,
            "dateModified": self.last_published_at.isoformat() if self.last_published_at else None,
            "author": {
                "@type": "Organization",
                "name": "Ubongo IQ"
            },
            "publisher": {
                "@type": "Organization", 
                "name": "Ubongo IQ",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://ubongoiq.com/static/img/logo.png"
                }
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": self.get_canonical_url()
            }
        }

        if hasattr(self, 'featured_image') and self.featured_image:
            try:
                rendition = self.featured_image.get_rendition('width-1200|height-630')
                data['image'] = rendition.url
            except Exception:
                pass

        if hasattr(self, 'category') and self.category:
            data['articleSection'] = self.category.name

        if hasattr(self, 'tags') and self.tags.exists():
            data['keywords'] = [tag.name for tag in self.tags.all()]

        if hasattr(self, 'reading_time_minutes'):
            data['timeRequired'] = f"PT{self.reading_time_minutes}M"

        return data

    def get_breadcrumb_data(self):
        items = [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "https://ubongoiq.com/"
            },
            {
                "@type": "ListItem", 
                "position": 2,
                "name": "Blog",
                "item": "https://ubongoiq.com/blog/"
            }
        ]

        if hasattr(self, 'category') and self.category:
            items.append(
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": self.category.name,
                    "item": f"https://ubongoiq.com/blog/category/{self.category.slug}/",
                }
            )
            position = 4
        else:
            position = 3

        items.append({
            "@type": "ListItem",
            "position": position,
            "name": self.title,
            "item": self.get_canonical_url()
        })

        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": items
        }


class CustomSitemap(Sitemap):
    def items(self):
        return Page.objects.live().public().order_by('-last_published_at')

    def lastmod(self, obj):
        return obj.last_published_at or obj.first_published_at

    def priority(self, obj):
        from blog.models import ArticlePage, BlogIndexPage
        from home.models import HomePage

        if isinstance(obj, HomePage):
            return 1.0
        elif isinstance(obj, BlogIndexPage):
            return 0.9
        elif isinstance(obj, ArticlePage):
            priority = 0.8
            if hasattr(obj, 'featured') and obj.featured:
                priority = 0.9
            return priority

        return 0.5

    def changefreq(self, obj):
        from blog.models import ArticlePage, BlogIndexPage
        from home.models import HomePage

        if isinstance(obj, HomePage):
            return 'daily'
        elif isinstance(obj, BlogIndexPage):
            return 'daily'
        elif isinstance(obj, ArticlePage):
            return 'weekly'

        return 'monthly'


def generate_robots_txt():
    from django.conf import settings

    domain = getattr(settings, "SITE_DOMAIN", "ubongoiq.com")
    return f"""User-agent: *
Allow: /

Sitemap: https://{domain}/sitemap.xml

Crawl-delay: 1

Disallow: /admin/
Disallow: /django-admin/
Disallow: /wagtail-admin/

Disallow: /api/

Disallow: /search?

Allow: /static/css/
Allow: /static/js/
Allow: /media/

Disallow: /static/admin/
Disallow: /static/wagtailadmin/
"""

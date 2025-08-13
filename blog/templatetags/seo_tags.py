from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()


@register.inclusion_tag('blog/seo/meta_tags.html', takes_context=True)
def render_seo_meta(context, page=None):
    if not page:
        page = context.get('page') or context.get('self')
    
    if not page:
        return {}
    
    meta_title = getattr(page, 'seo_title', None) or getattr(page, 'title', 'Ubongo IQ')
    if hasattr(page, 'get_meta_title'):
        meta_title = page.get_meta_title()
        
    meta_description = getattr(page, 'search_description', '') or getattr(page, 'intro', '')
    if hasattr(page, 'get_meta_description'):
        meta_description = page.get_meta_description()
    
    canonical_url = ''
    if hasattr(page, 'get_canonical_url'):
        canonical_url = page.get_canonical_url()
    elif hasattr(page, 'get_url'):
        canonical_url = f"https://ubongoiq.com{page.get_url()}"
    
    og_data = {}
    twitter_data = {}
    
    if hasattr(page, 'get_open_graph_data'):
        og_data = page.get_open_graph_data()
    else:
        og_data = {
            'title': meta_title,
            'description': meta_description,
            'url': canonical_url,
            'type': 'website',
            'site_name': 'Ubongo IQ'
        }
        
        if hasattr(page, 'featured_image') and page.featured_image:
            try:
                from wagtail.images import get_image_model
                Image = get_image_model()
                if isinstance(page.featured_image, Image):
                    rendition = page.featured_image.get_rendition('width-1200|height-630')
                    og_data['image'] = rendition.url
                    og_data['image_width'] = '1200'
                    og_data['image_height'] = '630'
            except:
                pass
    
    if hasattr(page, 'get_twitter_card_data'):
        twitter_data = page.get_twitter_card_data()
    else:
        twitter_data = {
            'card': 'summary_large_image',
            'title': meta_title,
            'description': meta_description
        }
        
        if hasattr(page, 'featured_image') and page.featured_image:
            try:
                from wagtail.images import get_image_model
                Image = get_image_model()
                if isinstance(page.featured_image, Image):
                    rendition = page.featured_image.get_rendition('width-1200|height-600')
                    twitter_data['image'] = rendition.url
            except:
                pass
    
    return {
        'page': page,
        'request': context.get('request'),
        'meta_title': meta_title,
        'meta_description': meta_description,
        'canonical_url': canonical_url,
        'og_data': og_data,
        'twitter_data': twitter_data,
    }


@register.simple_tag
def structured_data(page):
    if hasattr(page, 'get_structured_data'):
        data = page.get_structured_data()
        return mark_safe(
            f'<script type="application/ld+json">{json.dumps(data, indent=2)}</script>'
        )
    return ''


@register.simple_tag
def breadcrumb_data(page):
    if hasattr(page, 'get_breadcrumb_data'):
        data = page.get_breadcrumb_data()
        return mark_safe(
            f'<script type="application/ld+json">{json.dumps(data, indent=2)}</script>'
        )
    return ''


@register.inclusion_tag('blog/seo/breadcrumbs.html', takes_context=True)
def render_breadcrumbs(context, page=None):
    if not page:
        page = context.get('page') or context.get('self')
    
    breadcrumbs = []
    current = page
    
    while current:
        breadcrumbs.append({
            'title': current.title,
            'url': current.get_url() if current != page else None
        })
        current = current.get_parent()
        if hasattr(current, 'content_type') and current.content_type.model == 'page':
            break
    
    breadcrumbs.reverse()
    
    return {
        'breadcrumbs': breadcrumbs,
        'current_page': page
    }


@register.filter
def truncate_words_html(value, num_words):
    from django.utils.html import strip_tags
    from django.utils.text import Truncator
    
    plain_text = strip_tags(str(value))
    truncator = Truncator(plain_text)
    return truncator.words(num_words, html=True)


@register.simple_tag
def get_related_articles(article, limit=3):
    if not hasattr(article, 'category') or not hasattr(article, 'tags'):
        return []
    
    from blog.models import ArticlePage
    from django.db.models import Q, Count
    
    related = ArticlePage.objects.live().public().exclude(pk=article.pk)
    
    if article.category:
        related = related.filter(category=article.category)
    
    if article.tags.exists():
        tag_names = list(article.tags.values_list('name', flat=True))
        related = related.filter(tags__name__in=tag_names).distinct()
        
        related = related.annotate(
            tag_matches=Count('tags', filter=Q(tags__name__in=tag_names))
        ).order_by('-tag_matches', '-first_published_at')
    else:
        related = related.order_by('-first_published_at')
    
    return related[:limit]
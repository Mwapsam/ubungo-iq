"""
Template tags for cache busting in development
"""
import time
from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_cachebust(path):
    """
    Add cache busting parameter to static files in development
    """
    if settings.DEBUG:
        timestamp = str(int(time.time()))
        static_url = static(path)
        separator = '&' if '?' in static_url else '?'
        return f"{static_url}{separator}v={timestamp}"
    else:
        return static(path)


@register.simple_tag  
def css_cachebust(path):
    """
    Add cache busting specifically for CSS files
    """
    return static_cachebust(path)


@register.simple_tag
def js_cachebust(path):
    """
    Add cache busting specifically for JS files
    """
    return static_cachebust(path)
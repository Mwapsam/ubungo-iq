# ubongo/middleware.py
import time
from django.core.cache import cache
from django.http import HttpResponseTooManyRequests
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware to prevent abuse."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        if settings.DEBUG:
            return None
            
        # Get client IP
        ip = self.get_client_ip(request)
        
        # Different limits for different endpoints
        if request.path.startswith('/api/'):
            return self.check_rate_limit(ip, 'api', 60, 120)  # 60 requests per 2 minutes for API
        elif request.method == 'POST':
            return self.check_rate_limit(ip, 'post', 20, 300)  # 20 POST requests per 5 minutes
        else:
            return self.check_rate_limit(ip, 'general', 200, 300)  # 200 requests per 5 minutes
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def check_rate_limit(self, ip, prefix, limit, window):
        """Check if request exceeds rate limit."""
        cache_key = f"rate_limit_{prefix}_{ip}"
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= limit:
            return HttpResponseTooManyRequests(
                "Rate limit exceeded. Please try again later."
            )
        
        cache.set(cache_key, current_requests + 1, window)
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add comprehensive security headers."""
    
    def process_response(self, request, response):
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https: blob:",
            "media-src 'self' https:",
            "connect-src 'self'",
            "frame-src 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        
        return response


class ViewCountMiddleware(MiddlewareMixin):
    """Middleware to handle view counting efficiently."""
    
    def process_response(self, request, response):
        # Only count views for successful GET requests to article pages
        if (request.method == 'GET' and 
            response.status_code == 200 and
            hasattr(request, '_view_count_data')):
            
            from blog.tasks import increment_view_count_async
            increment_view_count_async.delay(
                request._view_count_data['page_id'],
                request._view_count_data['ip_address']
            )
            
        return response
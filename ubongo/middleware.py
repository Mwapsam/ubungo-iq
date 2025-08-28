import time
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils.cache import add_never_cache_headers
from django.http import HttpResponse


class HttpResponseTooManyRequests(HttpResponse):
    status_code = 429


class RateLimitMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        if settings.DEBUG:
            return None

        ip = self.get_client_ip(request)

        if request.path.startswith("/api/"):
            return self.check_rate_limit(ip, "api", 60, 120)
        elif request.method == "POST":
            return self.check_rate_limit(ip, "post", 20, 300)
        else:
            return self.check_rate_limit(ip, "general", 200, 300)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def check_rate_limit(self, ip, prefix, limit, window):
        cache_key = f"rate_limit_{prefix}_{ip}"
        current_requests = cache.get(cache_key, 0)

        if current_requests >= limit:
            return HttpResponseTooManyRequests(
                "Rate limit exceeded. Please try again later."
            )

        cache.set(cache_key, current_requests + 1, window)
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response["X-Content-Type-Options"] = "nosniff"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class ViewCountMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if (
            request.method == "GET"
            and response.status_code == 200
            and hasattr(request, "_view_count_data")
        ):

            from blog.tasks import increment_view_count_async

            increment_view_count_async.delay(
                request._view_count_data["page_id"],
                request._view_count_data["ip_address"],
            )

        return response


class DisableCacheMiddleware(MiddlewareMixin):
    """
    Middleware to disable caching in development for better developer experience
    """
    
    def process_response(self, request, response):
        # Only apply in development
        if settings.DEBUG:
            # Aggressive cache prevention for all requests
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Last-Modified'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
            response['ETag'] = f'"{int(time.time())}"'
            
            # Additional headers to prevent caching
            if request.path.startswith('/static/') or request.path.startswith('/media/'):
                response['Vary'] = 'Accept-Encoding'
            else:
                # For HTML pages, add additional no-cache headers
                add_never_cache_headers(response)
                response['X-Accel-Expires'] = '0'
                
        return response

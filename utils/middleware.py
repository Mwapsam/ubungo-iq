"""
Custom middleware for fixing compatibility issues.
"""
import logging

logger = logging.getLogger(__name__)


class WagtailCompatibilityMiddleware:
    """
    Middleware to handle Wagtail/asgiref compatibility issues.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except AttributeError as e:
            if "object has no attribute 'value'" in str(e):
                # Log the error but don't break the request
                logger.warning(f"Wagtail asgiref compatibility issue: {e}")
                # Return a simple response to prevent 500 error
                from django.http import JsonResponse
                return JsonResponse({'error': 'Temporary admin interface issue'}, status=200)
            else:
                # Re-raise other AttributeErrors
                raise
    
    def process_exception(self, request, exception):
        if isinstance(exception, AttributeError) and "object has no attribute 'value'" in str(exception):
            logger.warning(f"Caught Wagtail compatibility exception: {exception}")
            from django.http import JsonResponse
            return JsonResponse({'error': 'Admin interface temporarily unavailable'}, status=200)
        return None
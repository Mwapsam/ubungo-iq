# blog/analytics.py
import logging
import time
from functools import wraps
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
import json

logger = logging.getLogger('ubongo.analytics')
perf_logger = logging.getLogger('performance')


class AnalyticsCollector:
    """Centralized analytics data collector."""
    
    def __init__(self):
        self.events = []
    
    def track_event(self, event_type, data, user_id=None, session_id=None):
        """Track a custom event."""
        event = {
            'timestamp': timezone.now().isoformat(),
            'event_type': event_type,
            'data': data,
            'user_id': user_id,
            'session_id': session_id,
        }
        
        # Log event
        logger.info(f"Analytics event: {event_type}", extra=event)
        
        # Cache for real-time processing
        cache_key = f"analytics_event:{int(time.time())}"
        cache.set(cache_key, event, 3600)  # 1 hour
        
        return event
    
    def track_page_view(self, request, page_id, page_type=None):
        """Track page view with context."""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referer = request.META.get('HTTP_REFERER', '')
        ip_address = self.get_client_ip(request)
        
        data = {
            'page_id': page_id,
            'page_type': page_type or 'unknown',
            'ip_address': ip_address,
            'user_agent': user_agent,
            'referer': referer,
            'path': request.path,
            'method': request.method,
        }
        
        return self.track_event('page_view', data, 
                              session_id=request.session.session_key)
    
    def track_search(self, request, query, results_count=None):
        """Track search queries."""
        data = {
            'query': query,
            'results_count': results_count,
            'ip_address': self.get_client_ip(request),
        }
        
        return self.track_event('search', data,
                              session_id=request.session.session_key)
    
    def track_user_action(self, request, action, target=None, metadata=None):
        """Track user interactions."""
        data = {
            'action': action,
            'target': target,
            'metadata': metadata or {},
            'ip_address': self.get_client_ip(request),
        }
        
        return self.track_event('user_action', data,
                              session_id=request.session.session_key)
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# Global analytics collector instance
analytics = AnalyticsCollector()


def performance_monitor(func_name=None):
    """Decorator to monitor function performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not getattr(settings, 'PERFORMANCE_LOGGING_ENABLED', False):
                return func(*args, **kwargs)
            
            start_time = time.time()
            function_name = func_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log performance
                perf_logger.info(
                    f"Function executed: {function_name}",
                    extra={
                        'duration': duration,
                        'name': function_name,
                        'status': 'success'
                    }
                )
                
                # Track slow operations
                threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 1.0)
                if duration > threshold:
                    perf_logger.warning(
                        f"Slow operation detected: {function_name}",
                        extra={
                            'duration': duration,
                            'threshold': threshold,
                            'name': function_name
                        }
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                perf_logger.error(
                    f"Function failed: {function_name}",
                    extra={
                        'duration': duration,
                        'name': function_name,
                        'error': str(e),
                        'status': 'error'
                    }
                )
                raise
                
        return wrapper
    return decorator


class DatabasePerformanceMonitor:
    """Monitor database query performance."""
    
    def __init__(self):
        self.query_count = 0
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.query_count = len(connection.queries)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not getattr(settings, 'PERFORMANCE_LOGGING_ENABLED', False):
            return
            
        duration = time.time() - self.start_time
        new_queries = len(connection.queries) - self.query_count
        
        perf_logger.info(
            "Database performance",
            extra={
                'query_count': new_queries,
                'duration': duration,
                'queries_per_second': new_queries / duration if duration > 0 else 0
            }
        )
        
        if new_queries > 20:  # Threshold for too many queries
            perf_logger.warning(
                f"High query count detected: {new_queries} queries",
                extra={
                    'query_count': new_queries,
                    'duration': duration
                }
            )


class RequestMetrics:
    """Collect request-level metrics."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.start_time = time.time()
        self.db_queries = len(connection.queries)
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_cache_hit(self):
        self.cache_hits += 1
    
    def record_cache_miss(self):
        self.cache_misses += 1
    
    def get_metrics(self):
        return {
            'duration': time.time() - self.start_time,
            'db_queries': len(connection.queries) - self.db_queries,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_ratio': (
                self.cache_hits / max(self.cache_hits + self.cache_misses, 1)
            ),
        }


class RealTimeAnalytics:
    """Real-time analytics dashboard data."""
    
    @staticmethod
    def get_current_stats():
        """Get current real-time statistics."""
        now = timezone.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Get cached stats or calculate them
        stats_key = f"realtime_stats:{now.hour}"
        stats = cache.get(stats_key)
        
        if not stats:
            from blog.models import ArticlePage
            from django.db.models import Count, Avg, Sum
            
            stats = {
                'timestamp': now.isoformat(),
                'total_articles': ArticlePage.objects.live().count(),
                'total_views': ArticlePage.objects.aggregate(
                    total=Sum('view_count')
                )['total'] or 0,
                'popular_articles': list(
                    ArticlePage.objects.live()
                    .order_by('-view_count')[:5]
                    .values('title', 'view_count', 'slug')
                ),
                'recent_articles': list(
                    ArticlePage.objects.live()
                    .order_by('-first_published_at')[:5]
                    .values('title', 'first_published_at', 'slug')
                ),
                'hourly_views': RealTimeAnalytics.get_hourly_views(),
            }
            
            # Cache for 5 minutes
            cache.set(stats_key, stats, 300)
        
        return stats
    
    @staticmethod
    def get_hourly_views():
        """Get hourly view statistics."""
        # This would typically come from a time-series database
        # For now, return mock data structure
        return {
            'labels': [f"{i}:00" for i in range(24)],
            'data': [0] * 24  # Would be populated with real data
        }
    
    @staticmethod
    def get_search_trends():
        """Get trending search queries."""
        search_key = "trending_searches"
        trends = cache.get(search_key, [])
        
        return {
            'trending_queries': trends[:10],
            'timestamp': timezone.now().isoformat()
        }


def log_slow_query(query_time_ms, query, params=None):
    """Log slow database queries."""
    if query_time_ms > 100:  # Log queries slower than 100ms
        perf_logger.warning(
            f"Slow query detected: {query_time_ms}ms",
            extra={
                'query_time_ms': query_time_ms,
                'query': query[:200],  # Truncate long queries
                'params': str(params)[:100] if params else None
            }
        )


def log_memory_usage():
    """Log current memory usage."""
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        perf_logger.info(
            "Memory usage",
            extra={
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent()
            }
        )
    except ImportError:
        pass  # psutil not available


class ErrorTracker:
    """Track and analyze application errors."""
    
    @staticmethod
    def track_error(error, request=None, extra_context=None):
        """Track application errors with context."""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': timezone.now().isoformat(),
        }
        
        if request:
            error_data.update({
                'path': request.path,
                'method': request.method,
                'ip_address': analytics.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            })
        
        if extra_context:
            error_data['context'] = extra_context
        
        # Log the error
        logger.error(
            f"Application error: {error_data['error_type']}",
            extra=error_data,
            exc_info=True
        )
        
        # Cache for error analysis
        error_key = f"error:{int(time.time())}"
        cache.set(error_key, error_data, 86400)  # 24 hours
        
        return error_data
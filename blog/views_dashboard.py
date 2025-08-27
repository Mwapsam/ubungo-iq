"""
Analytics dashboard views for market intelligence.
"""
import json
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Avg, Sum, Q

from blog.models_scraping import ScrapedData, ScrapingSource, ScrapingLog, TrendingTopic
from blog.analysis import MarketIntelligenceAnalyzer
from blog.content_templates import ContentTemplateGenerator
from blog.alerts import MarketAlertSystem


@staff_member_required
def dashboard_home(request):
    """Main analytics dashboard view."""
    
    # Get cached data or generate fresh data
    dashboard_data = cache.get('dashboard_data')
    
    if not dashboard_data:
        dashboard_data = generate_dashboard_data()
        cache.set('dashboard_data', dashboard_data, timeout=900)  # 15 minutes cache
    
    # Get recent alerts
    recent_alerts = cache.get('market_alerts', [])[:10]  # Top 10 alerts
    
    context = {
        'dashboard_data': dashboard_data,
        'recent_alerts': recent_alerts,
        'page_title': 'Market Intelligence Dashboard'
    }
    
    return render(request, 'blog/dashboard.html', context)


@staff_member_required
@cache_page(60 * 15)  # Cache for 15 minutes
def api_market_overview(request):
    """API endpoint for market overview data."""
    
    try:
        analyzer = MarketIntelligenceAnalyzer()
        report = analyzer.generate_comprehensive_report()
        
        overview = {
            'total_products': report.get('total_products', 0),
            'total_suppliers': report.get('supplier_intelligence', {}).get('total_suppliers', 0),
            'avg_price': report.get('pricing_analysis', {}).get('average_price', 0),
            'verification_rate': report.get('supplier_intelligence', {}).get('verification_rate', 0),
            'generated_at': report.get('generated_at').isoformat() if report.get('generated_at') else None
        }
        
        return JsonResponse({'success': True, 'data': overview})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
@cache_page(60 * 30)  # Cache for 30 minutes
def api_price_trends(request):
    """API endpoint for price trend data."""
    
    try:
        # Get price data over time (last 30 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Group by week for trend analysis
        price_data = []
        for i in range(4):  # 4 weeks
            week_start = start_date + timedelta(days=i*7)
            week_end = week_start + timedelta(days=7)
            
            week_items = ScrapedData.objects.filter(
                scraped_at__gte=week_start,
                scraped_at__lt=week_end,
                current_price__isnull=False
            )
            
            if week_items.exists():
                avg_price = week_items.aggregate(Avg('current_price'))['current_price__avg']
                price_data.append({
                    'week': f"Week {i+1}",
                    'date': week_start.strftime('%Y-%m-%d'),
                    'avg_price': round(avg_price, 2) if avg_price else 0,
                    'product_count': week_items.count()
                })
        
        return JsonResponse({'success': True, 'data': price_data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
@cache_page(60 * 30)  # Cache for 30 minutes  
def api_supplier_distribution(request):
    """API endpoint for supplier geographic distribution."""
    
    try:
        # Get supplier distribution by country
        country_data = ScrapedData.objects.filter(
            supplier_country__isnull=False
        ).values('supplier_country').annotate(
            count=Count('id'),
            verified_count=Count('id', filter=Q(verification_status='Verified'))
        ).order_by('-count')[:10]
        
        supplier_data = []
        for item in country_data:
            country = item['supplier_country']
            total = item['count']
            verified = item['verified_count']
            verification_rate = (verified / total * 100) if total > 0 else 0
            
            supplier_data.append({
                'country': country,
                'total_suppliers': total,
                'verified_suppliers': verified,
                'verification_rate': round(verification_rate, 1)
            })
        
        return JsonResponse({'success': True, 'data': supplier_data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
@cache_page(60 * 15)  # Cache for 15 minutes
def api_trending_topics(request):
    """API endpoint for trending topics."""
    
    try:
        trending_topics = TrendingTopic.objects.filter(
            first_seen__gte=timezone.now() - timedelta(days=7)
        ).order_by('-frequency')[:10]
        
        topics_data = []
        for topic in trending_topics:
            topics_data.append({
                'topic': topic.topic,
                'category': topic.category,
                'frequency': topic.frequency,
                'trending_score': topic.frequency,  # Use frequency as trending score
                'total_views': topic.total_views
            })
        
        return JsonResponse({'success': True, 'data': topics_data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
def api_scraping_health(request):
    """API endpoint for scraping system health status."""
    
    try:
        # Get recent scraping activity (last 24 hours)
        recent_cutoff = timezone.now() - timedelta(hours=24)
        
        sources = ScrapingSource.objects.filter(enabled=True)
        health_data = {
            'total_sources': sources.count(),
            'healthy_sources': sources.filter(consecutive_failures=0).count(),
            'failing_sources': sources.filter(consecutive_failures__gte=3).count(),
            'recent_scrapes': ScrapingLog.objects.filter(
                started_at__gte=recent_cutoff
            ).count(),
            'success_rate': 0
        }
        
        recent_logs = ScrapingLog.objects.filter(started_at__gte=recent_cutoff)
        if recent_logs.exists():
            successful_scrapes = recent_logs.filter(status='success').count()
            total_scrapes = recent_logs.count()
            health_data['success_rate'] = round((successful_scrapes / total_scrapes * 100), 1)
        
        # Get recent scraping activity by source
        source_activity = []
        for source in sources[:10]:  # Top 10 sources
            recent_logs = source.logs.filter(started_at__gte=recent_cutoff)
            
            source_activity.append({
                'name': source.name,
                'website': source.website,
                'last_scraped': source.last_scraped.isoformat() if source.last_scraped else None,
                'consecutive_failures': source.consecutive_failures,
                'is_healthy': source.is_healthy,
                'recent_scrapes': recent_logs.count(),
                'recent_success_rate': calculate_success_rate(recent_logs)
            })
        
        health_data['source_activity'] = source_activity
        
        return JsonResponse({'success': True, 'data': health_data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
def api_content_opportunities(request):
    """API endpoint for content generation opportunities."""
    
    try:
        generator = ContentTemplateGenerator()
        templates = generator.generate_all_templates()
        
        opportunities = []
        for template in templates:
            if 'error' not in template:
                opportunities.append({
                    'title': template['title'],
                    'content_type': template['content_type'],
                    'data_confidence': template['data_confidence'],
                    'word_count': len(template['content'].split()) if template.get('content') else 0,
                    'tags': template.get('tags', [])[:3],  # First 3 tags
                    'meta_description': template.get('meta_description', '')[:100] + '...'
                })
        
        return JsonResponse({'success': True, 'data': opportunities})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
def api_alerts_summary(request):
    """API endpoint for alerts summary."""
    
    try:
        # Get cached alerts
        alerts = cache.get('market_alerts', [])
        
        alert_summary = {
            'total_alerts': len(alerts),
            'critical': len([a for a in alerts if hasattr(a, 'level') and a.level.value == 'critical']),
            'high': len([a for a in alerts if hasattr(a, 'level') and a.level.value == 'high']),
            'medium': len([a for a in alerts if hasattr(a, 'level') and a.level.value == 'medium']),
            'low': len([a for a in alerts if hasattr(a, 'level') and a.level.value == 'low'])
        }
        
        # Recent alerts data
        recent_alerts = []
        for alert in alerts[:5]:  # Top 5 alerts
            if hasattr(alert, 'title'):
                recent_alerts.append({
                    'title': alert.title,
                    'message': alert.message,
                    'level': alert.level.value if hasattr(alert, 'level') else 'unknown',
                    'affected_products': getattr(alert, 'affected_products', 0),
                    'created_at': alert.created_at.isoformat() if hasattr(alert, 'created_at') else None
                })
        
        alert_summary['recent_alerts'] = recent_alerts
        
        return JsonResponse({'success': True, 'data': alert_summary})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def generate_dashboard_data():
    """Generate comprehensive dashboard data."""
    
    try:
        # Get basic statistics
        total_products = ScrapedData.objects.count()
        total_sources = ScrapingSource.objects.filter(enabled=True).count()
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_products = ScrapedData.objects.filter(scraped_at__gte=week_ago).count()
        recent_scrapes = ScrapingLog.objects.filter(started_at__gte=week_ago).count()
        
        # Price statistics
        price_stats = ScrapedData.objects.filter(
            current_price__isnull=False
        ).aggregate(
            avg_price=Avg('current_price'),
            min_price=Avg('current_price'),  # Using Avg to avoid None issues
            max_price=Avg('current_price')
        )
        
        # Supplier statistics
        supplier_stats = ScrapedData.objects.filter(
            supplier_country__isnull=False
        ).aggregate(
            total_suppliers=Count('supplier_name', distinct=True),
            verified_suppliers=Count('supplier_name', 
                                   filter=Q(verification_status='Verified'), 
                                   distinct=True)
        )
        
        verification_rate = 0
        if supplier_stats['total_suppliers']:
            verification_rate = (supplier_stats['verified_suppliers'] / 
                               supplier_stats['total_suppliers'] * 100)
        
        # Category breakdown
        category_data = list(ScrapedData.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count')[:5])
        
        dashboard_data = {
            'overview': {
                'total_products': total_products,
                'total_sources': total_sources,
                'recent_products': recent_products,
                'recent_scrapes': recent_scrapes,
                'avg_price': round(price_stats['avg_price'], 2) if price_stats['avg_price'] else 0,
                'verification_rate': round(verification_rate, 1)
            },
            'categories': category_data,
            'generated_at': timezone.now().isoformat()
        }
        
        return dashboard_data
        
    except Exception as e:
        return {
            'overview': {
                'total_products': 0,
                'total_sources': 0,
                'recent_products': 0,
                'recent_scrapes': 0,
                'avg_price': 0,
                'verification_rate': 0
            },
            'categories': [],
            'generated_at': timezone.now().isoformat(),
            'error': str(e)
        }


def calculate_success_rate(logs):
    """Calculate success rate for scraping logs."""
    if not logs.exists():
        return 0
    
    successful = logs.filter(status='success').count()
    total = logs.count()
    
    return round((successful / total * 100), 1) if total > 0 else 0
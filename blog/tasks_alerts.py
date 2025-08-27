import logging
from datetime import timedelta
from typing import List

from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.models import User

from blog.alerts import MarketAlertSystem, MarketAlert, AlertLevel
from blog.models_scraping import ScrapingLog

logger = logging.getLogger(__name__)


@shared_task
def monitor_market_changes():
    try:
        alert_system = MarketAlertSystem()
        alerts = alert_system.monitor_market_changes()
        
        if alerts:
            cache.set('market_alerts', alerts, timeout=3600)  
            
            critical_high_alerts = [
                a for a in alerts 
                if a.level in [AlertLevel.CRITICAL, AlertLevel.HIGH]
            ]
            
            if critical_high_alerts:
                send_alert_notifications.delay([a.__dict__ for a in critical_high_alerts])
            
            logger.info(f"Market monitoring completed: {len(alerts)} alerts generated")
            return {
                'success': True,
                'alerts_generated': len(alerts),
                'critical_alerts': len([a for a in alerts if a.level == AlertLevel.CRITICAL]),
                'high_alerts': len([a for a in alerts if a.level == AlertLevel.HIGH])
            }
        else:
            logger.info("Market monitoring completed: No alerts generated")
            return {'success': True, 'alerts_generated': 0}
            
    except Exception as e:
        logger.error(f"Market monitoring failed: {e}")
        return {'error': str(e)}


@shared_task
def send_alert_notifications(alert_dicts: List[dict]):
    try:
        alerts = []
        for alert_dict in alert_dicts:
            class SimpleAlert:
                def __init__(self, data):
                    self.level = data.get('level')
                    self.title = data.get('title')
                    self.message = data.get('message')
                    self.action_required = data.get('action_required')
                    self.affected_products = data.get('affected_products')
            
            alerts.append(SimpleAlert(alert_dict))
        
        recipients = list(User.objects.filter(
            is_superuser=True,
            email__isnull=False
        ).exclude(email='').values_list('email', flat=True))
        
        if not recipients:
            logger.warning("No email recipients found for alert notifications")
            return {'error': 'No recipients'}
        
        alert_system = MarketAlertSystem()
        success = alert_system.send_alert_notifications(alerts, recipients)
        
        if success:
            logger.info(f"Alert notifications sent successfully to {len(recipients)} recipients")
            return {'success': True, 'recipients': len(recipients)}
        else:
            return {'error': 'Failed to send notifications'}
            
    except Exception as e:
        logger.error(f"Failed to send alert notifications: {e}")
        return {'error': str(e)}


@shared_task
def check_scraping_health():
    try:
        from blog.models_scraping import ScrapingSource
        
        failing_sources = ScrapingSource.objects.filter(
            enabled=True,
            consecutive_failures__gte=3
        )
        
        stale_cutoff = timezone.now() - timedelta(days=2)
        stale_sources = ScrapingSource.objects.filter(
            enabled=True,
            last_scraped__lt=stale_cutoff
        )
        
        health_alerts = []
        
        if failing_sources.exists():
            health_alerts.append({
                'type': 'scraping_failure',
                'level': 'high',
                'title': f"Scraping Failures Detected",
                'message': f"{failing_sources.count()} sources have 3+ consecutive failures",
                'action_required': "Check scraping logs and fix configuration issues",
                'affected_products': 0
            })
        
        if stale_sources.exists():
            health_alerts.append({
                'type': 'stale_data',
                'level': 'medium',
                'title': f"Stale Data Sources",
                'message': f"{stale_sources.count()} sources haven't scraped in 48+ hours",
                'action_required': "Review scraping schedules and source availability",
                'affected_products': 0
            })
        
        if health_alerts:
            send_alert_notifications.delay(health_alerts)
            logger.info(f"Scraping health check: {len(health_alerts)} issues detected")
        else:
            logger.info("Scraping health check: All systems operational")
        
        return {
            'success': True,
            'failing_sources': failing_sources.count(),
            'stale_sources': stale_sources.count(),
            'alerts_sent': len(health_alerts)
        }
        
    except Exception as e:
        logger.error(f"Scraping health check failed: {e}")
        return {'error': str(e)}


@shared_task
def generate_daily_market_summary():
    """Generate a daily market intelligence summary."""
    try:
        from blog.analysis import MarketIntelligenceAnalyzer
        from blog.content_templates import ContentTemplateGenerator
        
        # Generate comprehensive market report
        analyzer = MarketIntelligenceAnalyzer()
        report = analyzer.generate_comprehensive_report()
        
        # Generate content opportunities
        generator = ContentTemplateGenerator()
        templates = generator.generate_all_templates()
        
        # Cache the daily summary
        summary = {
            'generated_at': timezone.now(),
            'market_report': report,
            'content_templates': len(templates),
            'content_opportunities': report.get('content_opportunities', [])[:5]
        }
        
        cache.set('daily_market_summary', summary, timeout=86400)  # 24 hour cache
        
        logger.info("Daily market summary generated successfully")
        return {
            'success': True,
            'total_products': report.get('total_products', 0),
            'content_templates': len(templates),
            'opportunities': len(report.get('content_opportunities', []))
        }
        
    except Exception as e:
        logger.error(f"Daily market summary generation failed: {e}")
        return {'error': str(e)}


@shared_task
def cleanup_old_alerts():
    """Clean up old cached alerts and logs."""
    try:
        # Clean up old scraping logs (keep 30 days)
        old_cutoff = timezone.now() - timedelta(days=30)
        old_logs = ScrapingLog.objects.filter(started_at__lt=old_cutoff)
        deleted_count = old_logs.count()
        old_logs.delete()
        
        logger.info(f"Cleaned up {deleted_count} old scraping logs")
        return {'success': True, 'cleaned_logs': deleted_count}
        
    except Exception as e:
        logger.error(f"Alert cleanup failed: {e}")
        return {'error': str(e)}


# Periodic task scheduling helper
def schedule_market_monitoring():
    """Helper function to set up periodic monitoring tasks."""
    from django_celery_beat.models import PeriodicTask, IntervalSchedule
    
    # Create schedules
    every_30_minutes, _ = IntervalSchedule.objects.get_or_create(
        every=30,
        period=IntervalSchedule.MINUTES,
    )
    
    every_6_hours, _ = IntervalSchedule.objects.get_or_create(
        every=6,
        period=IntervalSchedule.HOURS,
    )
    
    daily, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period=IntervalSchedule.DAYS,
    )
    
    # Create periodic tasks
    PeriodicTask.objects.update_or_create(
        name='Monitor Market Changes',
        defaults={
            'task': 'blog.tasks_alerts.monitor_market_changes',
            'interval': every_30_minutes,
            'enabled': True
        }
    )
    
    PeriodicTask.objects.update_or_create(
        name='Check Scraping Health',
        defaults={
            'task': 'blog.tasks_alerts.check_scraping_health',
            'interval': every_6_hours,
            'enabled': True
        }
    )
    
    PeriodicTask.objects.update_or_create(
        name='Generate Daily Market Summary',
        defaults={
            'task': 'blog.tasks_alerts.generate_daily_market_summary',
            'interval': daily,
            'enabled': True
        }
    )
    
    PeriodicTask.objects.update_or_create(
        name='Cleanup Old Alerts',
        defaults={
            'task': 'blog.tasks_alerts.cleanup_old_alerts',
            'interval': daily,
            'enabled': True
        }
    )
    
    logger.info("Market monitoring periodic tasks scheduled successfully")
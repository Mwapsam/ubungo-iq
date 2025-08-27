"""
Management command to run market monitoring and alerts.
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone

from blog.alerts import MarketAlertSystem, AlertLevel
from blog.tasks_alerts import schedule_market_monitoring


class Command(BaseCommand):
    help = 'Run market monitoring and generate alerts'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--test-mode',
            action='store_true',
            help='Run in test mode (display alerts without sending notifications)'
        )
        parser.add_argument(
            '--setup-scheduler',
            action='store_true',
            help='Set up periodic task scheduler for automated monitoring'
        )
        parser.add_argument(
            '--send-notifications',
            action='store_true',
            help='Send email notifications for high-priority alerts'
        )
        parser.add_argument(
            '--show-cached',
            action='store_true',
            help='Show cached alerts from previous runs'
        )
    
    def handle(self, *args, **options):
        if options['setup_scheduler']:
            self.setup_scheduler()
            return
        
        if options['show_cached']:
            self.show_cached_alerts()
            return
        
        # Run market monitoring
        self.stdout.write(self.style.SUCCESS('🔍 Starting Market Intelligence Monitoring...'))
        
        try:
            alert_system = MarketAlertSystem()
            alerts = alert_system.monitor_market_changes()
            
            if not alerts:
                self.stdout.write(self.style.SUCCESS('✅ No alerts detected - market conditions stable'))
                return
            
            # Display alerts summary
            self.display_alerts_summary(alerts)
            
            # Display detailed alerts
            self.display_alerts_detail(alerts)
            
            # Cache alerts for dashboard
            cache.set('market_alerts', alerts, timeout=3600)
            
            # Send notifications if requested and not in test mode
            if options['send_notifications'] and not options['test_mode']:
                self.send_notifications(alert_system, alerts)
            elif options['test_mode']:
                self.stdout.write(self.style.WARNING('📧 Test mode: Notifications not sent'))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Market monitoring failed: {e}')
            )
    
    def display_alerts_summary(self, alerts):
        """Display summary of alerts by level."""
        critical_count = len([a for a in alerts if a.level == AlertLevel.CRITICAL])
        high_count = len([a for a in alerts if a.level == AlertLevel.HIGH])
        medium_count = len([a for a in alerts if a.level == AlertLevel.MEDIUM])
        low_count = len([a for a in alerts if a.level == AlertLevel.LOW])
        
        self.stdout.write(f'📊 ALERT SUMMARY - Generated at {timezone.now().strftime("%Y-%m-%d %H:%M")}')
        self.stdout.write('=' * 60)
        
        if critical_count:
            self.stdout.write(self.style.ERROR(f'🚨 CRITICAL: {critical_count} alerts'))
        if high_count:
            self.stdout.write(self.style.WARNING(f'⚠️  HIGH: {high_count} alerts'))
        if medium_count:
            self.stdout.write(f'ℹ️  MEDIUM: {medium_count} alerts')
        if low_count:
            self.stdout.write(f'💡 LOW: {low_count} alerts')
        
        self.stdout.write('')
    
    def display_alerts_detail(self, alerts):
        """Display detailed alert information."""
        for i, alert in enumerate(alerts, 1):
            # Choose style based on alert level
            if alert.level == AlertLevel.CRITICAL:
                style = self.style.ERROR
                icon = '🚨'
            elif alert.level == AlertLevel.HIGH:
                style = self.style.WARNING
                icon = '⚠️ '
            elif alert.level == AlertLevel.MEDIUM:
                style = self.style.SUCCESS  # Using SUCCESS for blue/cyan color
                icon = 'ℹ️ '
            else:
                style = self.style.NOTICE if hasattr(self.style, 'NOTICE') else lambda x: x
                icon = '💡'
            
            self.stdout.write(style(f'{icon} ALERT #{i} - {alert.level.value.upper()}'))
            self.stdout.write(f'   Title: {alert.title}')
            self.stdout.write(f'   Message: {alert.message}')
            self.stdout.write(f'   Affected Products: {alert.affected_products}')
            self.stdout.write(f'   Action Required: {alert.action_required}')
            self.stdout.write(f'   Urgency Score: {alert.urgency_score}/100')
            
            # Show key data points
            if alert.data_points:
                key_data = []
                for key, value in alert.data_points.items():
                    if isinstance(value, float):
                        if key.endswith('_price') or key.endswith('_cost'):
                            key_data.append(f'{key}: ${value:.2f}')
                        elif key.endswith('_percent') or 'change' in key:
                            key_data.append(f'{key}: {value:.1f}%')
                        else:
                            key_data.append(f'{key}: {value:.2f}')
                    else:
                        key_data.append(f'{key}: {value}')
                
                if key_data:
                    self.stdout.write(f'   Key Data: {", ".join(key_data[:3])}')
            
            self.stdout.write('')  # Empty line between alerts
    
    def send_notifications(self, alert_system, alerts):
        """Send email notifications for alerts."""
        high_priority_alerts = [
            a for a in alerts 
            if a.level in [AlertLevel.CRITICAL, AlertLevel.HIGH]
        ]
        
        if high_priority_alerts:
            success = alert_system.send_alert_notifications(high_priority_alerts)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'📧 Email notifications sent for {len(high_priority_alerts)} high-priority alerts'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Failed to send email notifications')
                )
        else:
            self.stdout.write('📧 No high-priority alerts to send notifications for')
    
    def show_cached_alerts(self):
        """Display cached alerts from previous runs."""
        cached_alerts = cache.get('market_alerts')
        
        if not cached_alerts:
            self.stdout.write('📋 No cached alerts found')
            return
        
        self.stdout.write(f'📋 CACHED ALERTS ({len(cached_alerts)} total):')
        self.stdout.write('=' * 50)
        
        for i, alert in enumerate(cached_alerts, 1):
            self.stdout.write(f'{i}. {alert.title} ({alert.level.value})')
            self.stdout.write(f'   {alert.message}')
            self.stdout.write('')
    
    def setup_scheduler(self):
        """Set up periodic task scheduler."""
        try:
            schedule_market_monitoring()
            self.stdout.write(
                self.style.SUCCESS('✅ Market monitoring scheduler configured successfully!')
            )
            self.stdout.write('')
            self.stdout.write('📅 Scheduled Tasks:')
            self.stdout.write('   • Market Monitoring: Every 30 minutes')
            self.stdout.write('   • Scraping Health Check: Every 6 hours') 
            self.stdout.write('   • Daily Market Summary: Daily at midnight')
            self.stdout.write('   • Alert Cleanup: Daily')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to setup scheduler: {e}')
            )
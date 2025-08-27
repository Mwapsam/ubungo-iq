"""
Real-time market alerts and monitoring system.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from django.utils import timezone
from django.db.models import Avg, Count, Q, F
from django.core.mail import send_mail
from django.contrib.auth.models import User

from blog.models_scraping import ScrapedData, ScrapingSource
from blog.analysis import MarketIntelligenceAnalyzer

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    PRICE_SURGE = "price_surge"
    PRICE_DROP = "price_drop"
    SUPPLY_SHORTAGE = "supply_shortage"
    NEW_SUPPLIER = "new_supplier"
    VERIFICATION_CHANGE = "verification_change"
    DEMAND_SPIKE = "demand_spike"
    QUALITY_ISSUE = "quality_issue"
    MARKET_TREND = "market_trend"


@dataclass
class MarketAlert:
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    affected_products: int
    data_points: Dict[str, Any]
    created_at: datetime
    action_required: str
    urgency_score: int


class MarketAlertSystem:
    """Real-time market monitoring and alert system."""
    
    def __init__(self):
        self.analyzer = MarketIntelligenceAnalyzer()
        self.alert_thresholds = {
            'price_change': 15.0,  # % change threshold
            'supply_change': 25.0,  # % change in supplier count
            'demand_spike': 200.0,  # % increase in views/sales
            'quality_drop': 3.5,  # Rating threshold
            'verification_drop': 60.0  # % verified suppliers
        }
        
    def monitor_market_changes(self) -> List[MarketAlert]:
        """Monitor all market indicators and generate alerts."""
        alerts = []
        
        # Get recent data for comparison
        current_period = timezone.now() - timedelta(days=7)
        previous_period = timezone.now() - timedelta(days=14)
        
        current_data = ScrapedData.objects.filter(scraped_at__gte=current_period)
        previous_data = ScrapedData.objects.filter(
            scraped_at__gte=previous_period, 
            scraped_at__lt=current_period
        )
        
        # Generate different types of alerts
        alerts.extend(self._detect_price_changes(current_data, previous_data))
        alerts.extend(self._detect_supply_changes(current_data, previous_data))
        alerts.extend(self._detect_demand_changes(current_data, previous_data))
        alerts.extend(self._detect_quality_changes(current_data, previous_data))
        alerts.extend(self._detect_supplier_changes(current_data, previous_data))
        alerts.extend(self._detect_market_trends(current_data))
        
        # Sort by urgency and level
        alerts.sort(key=lambda x: (x.level.value, x.urgency_score), reverse=True)
        
        return alerts
    
    def _detect_price_changes(self, current_data, previous_data) -> List[MarketAlert]:
        """Detect significant price movements."""
        alerts = []
        
        # Calculate average prices by category
        current_prices = self._get_category_prices(current_data)
        previous_prices = self._get_category_prices(previous_data)
        
        for category, current_avg in current_prices.items():
            if category in previous_prices:
                previous_avg = previous_prices[category]
                change_percent = ((current_avg - previous_avg) / previous_avg) * 100
                
                if abs(change_percent) >= self.alert_thresholds['price_change']:
                    product_count = current_data.filter(category=category).count()
                    
                    if change_percent > 0:
                        alert_type = AlertType.PRICE_SURGE
                        level = AlertLevel.HIGH if change_percent > 25 else AlertLevel.MEDIUM
                        title = f"Price Surge Alert: {category.title()}"
                        message = f"Average prices increased {change_percent:.1f}% ({product_count} products)"
                        action = "Consider accelerating purchases before prices rise further"
                    else:
                        alert_type = AlertType.PRICE_DROP
                        level = AlertLevel.MEDIUM
                        title = f"Price Drop Opportunity: {category.title()}"
                        message = f"Average prices decreased {abs(change_percent):.1f}% ({product_count} products)"
                        action = "Opportunity to negotiate better prices or increase order volume"
                    
                    alerts.append(MarketAlert(
                        alert_type=alert_type,
                        level=level,
                        title=title,
                        message=message,
                        affected_products=product_count,
                        data_points={
                            'category': category,
                            'current_price': current_avg,
                            'previous_price': previous_avg,
                            'change_percent': change_percent
                        },
                        created_at=timezone.now(),
                        action_required=action,
                        urgency_score=int(abs(change_percent))
                    ))
        
        return alerts
    
    def _detect_supply_changes(self, current_data, previous_data) -> List[MarketAlert]:
        """Detect changes in supplier availability."""
        alerts = []
        
        current_suppliers = self._get_supplier_counts(current_data)
        previous_suppliers = self._get_supplier_counts(previous_data)
        
        for country, current_count in current_suppliers.items():
            if country in previous_suppliers:
                previous_count = previous_suppliers[country]
                change_percent = ((current_count - previous_count) / previous_count) * 100
                
                if change_percent < -self.alert_thresholds['supply_change']:
                    alerts.append(MarketAlert(
                        alert_type=AlertType.SUPPLY_SHORTAGE,
                        level=AlertLevel.HIGH,
                        title=f"Supply Shortage Alert: {country}",
                        message=f"Supplier count dropped {abs(change_percent):.1f}% in {country}",
                        affected_products=current_data.filter(supplier_country=country).count(),
                        data_points={
                            'country': country,
                            'current_suppliers': current_count,
                            'previous_suppliers': previous_count,
                            'change_percent': change_percent
                        },
                        created_at=timezone.now(),
                        action_required="Diversify supplier base or secure backup suppliers",
                        urgency_score=80
                    ))
        
        return alerts
    
    def _detect_demand_changes(self, current_data, previous_data) -> List[MarketAlert]:
        """Detect spikes in product demand."""
        alerts = []
        
        # Focus on products with significant view/sales increases
        demand_products = []
        
        for item in current_data:
            if item.views and item.views > 100:  # Only track popular products
                # Try to find same product in previous period
                previous_item = previous_data.filter(
                    external_id=item.external_id,
                    source=item.source
                ).first()
                
                if previous_item and previous_item.views:
                    view_increase = ((item.views - previous_item.views) / previous_item.views) * 100
                    
                    if view_increase >= self.alert_thresholds['demand_spike']:
                        demand_products.append({
                            'item': item,
                            'increase': view_increase,
                            'current_views': item.views,
                            'previous_views': previous_item.views
                        })
        
        if demand_products:
            # Group by category
            category_spikes = {}
            for product in demand_products:
                category = product['item'].category or 'uncategorized'
                if category not in category_spikes:
                    category_spikes[category] = []
                category_spikes[category].append(product)
            
            for category, products in category_spikes.items():
                if len(products) >= 3:  # At least 3 products showing spike
                    avg_increase = sum(p['increase'] for p in products) / len(products)
                    
                    alerts.append(MarketAlert(
                        alert_type=AlertType.DEMAND_SPIKE,
                        level=AlertLevel.MEDIUM,
                        title=f"Demand Spike: {category.title()}",
                        message=f"Average {avg_increase:.0f}% increase in views for {len(products)} products",
                        affected_products=len(products),
                        data_points={
                            'category': category,
                            'avg_increase': avg_increase,
                            'top_products': [p['item'].title for p in products[:3]]
                        },
                        created_at=timezone.now(),
                        action_required="Monitor inventory levels and consider increasing stock",
                        urgency_score=int(avg_increase / 10)
                    ))
        
        return alerts
    
    def _detect_quality_changes(self, current_data, previous_data) -> List[MarketAlert]:
        """Detect quality rating deterioration."""
        alerts = []
        
        # Calculate average ratings by supplier country
        current_ratings = self._get_country_ratings(current_data)
        previous_ratings = self._get_country_ratings(previous_data)
        
        for country, current_rating in current_ratings.items():
            if country in previous_ratings and current_rating < self.alert_thresholds['quality_drop']:
                previous_rating = previous_ratings[country]
                rating_drop = previous_rating - current_rating
                
                if rating_drop >= 0.3:  # Significant drop in rating
                    product_count = current_data.filter(supplier_country=country).count()
                    
                    alerts.append(MarketAlert(
                        alert_type=AlertType.QUALITY_ISSUE,
                        level=AlertLevel.HIGH,
                        title=f"Quality Alert: {country} Suppliers",
                        message=f"Average rating dropped {rating_drop:.1f} points to {current_rating:.1f}",
                        affected_products=product_count,
                        data_points={
                            'country': country,
                            'current_rating': current_rating,
                            'previous_rating': previous_rating,
                            'rating_drop': rating_drop
                        },
                        created_at=timezone.now(),
                        action_required="Review supplier quality and consider additional verification",
                        urgency_score=int(rating_drop * 20)
                    ))
        
        return alerts
    
    def _detect_supplier_changes(self, current_data, previous_data) -> List[MarketAlert]:
        """Detect changes in supplier verification status."""
        alerts = []
        
        current_verified = current_data.filter(verification_status='Verified').count()
        current_total = current_data.count()
        current_rate = (current_verified / current_total * 100) if current_total > 0 else 0
        
        previous_verified = previous_data.filter(verification_status='Verified').count()
        previous_total = previous_data.count()
        previous_rate = (previous_verified / previous_total * 100) if previous_total > 0 else 0
        
        if current_rate < self.alert_thresholds['verification_drop'] and current_rate < previous_rate:
            rate_drop = previous_rate - current_rate
            
            if rate_drop >= 5.0:  # 5% or more drop in verification rate
                alerts.append(MarketAlert(
                    alert_type=AlertType.VERIFICATION_CHANGE,
                    level=AlertLevel.MEDIUM,
                    title="Supplier Verification Rate Decline",
                    message=f"Verified suppliers dropped {rate_drop:.1f}% to {current_rate:.1f}%",
                    affected_products=current_total - current_verified,
                    data_points={
                        'current_rate': current_rate,
                        'previous_rate': previous_rate,
                        'rate_drop': rate_drop,
                        'unverified_products': current_total - current_verified
                    },
                    created_at=timezone.now(),
                    action_required="Review supplier verification processes and requirements",
                    urgency_score=int(rate_drop * 2)
                ))
        
        return alerts
    
    def _detect_market_trends(self, current_data) -> List[MarketAlert]:
        """Detect emerging market trends."""
        alerts = []
        
        # Use the analyzer to get trend insights
        try:
            report = self.analyzer.generate_comprehensive_report()
            trends = report.get('market_trends', {})
            
            # Check for strong trending categories
            top_categories = trends.get('top_performing_categories', {})
            if top_categories:
                top_category, avg_views = list(top_categories.items())[0]
                
                if avg_views > 1000:  # High view threshold
                    product_count = current_data.filter(category=top_category).count()
                    
                    alerts.append(MarketAlert(
                        alert_type=AlertType.MARKET_TREND,
                        level=AlertLevel.LOW,
                        title=f"Trending Category: {top_category.title()}",
                        message=f"Strong performance with {avg_views:.0f} average views",
                        affected_products=product_count,
                        data_points={
                            'category': top_category,
                            'avg_views': avg_views,
                            'trend_strength': 'high'
                        },
                        created_at=timezone.now(),
                        action_required="Consider expanding inventory in this trending category",
                        urgency_score=30
                    ))
        
        except Exception as e:
            logger.error(f"Error detecting market trends: {e}")
        
        return alerts
    
    def _get_category_prices(self, data) -> Dict[str, float]:
        """Calculate average prices by category."""
        category_prices = {}
        
        for category in data.values_list('category', flat=True).distinct():
            if category:
                prices = []
                for item in data.filter(category=category):
                    if item.current_price:
                        prices.append(float(item.current_price))
                
                if prices:
                    category_prices[category] = sum(prices) / len(prices)
        
        return category_prices
    
    def _get_supplier_counts(self, data) -> Dict[str, int]:
        """Count suppliers by country."""
        return dict(data.values('supplier_country').annotate(
            count=Count('supplier_name', distinct=True)
        ).values_list('supplier_country', 'count'))
    
    def _get_country_ratings(self, data) -> Dict[str, float]:
        """Calculate average ratings by supplier country."""
        country_ratings = {}
        
        for country in data.values_list('supplier_country', flat=True).distinct():
            if country:
                ratings = []
                for item in data.filter(supplier_country=country):
                    if item.rating and item.rating > 0:
                        ratings.append(float(item.rating))
                
                if ratings:
                    country_ratings[country] = sum(ratings) / len(ratings)
        
        return country_ratings
    
    def send_alert_notifications(self, alerts: List[MarketAlert], 
                               recipients: Optional[List[str]] = None) -> bool:
        """Send alert notifications to specified recipients."""
        if not alerts:
            return True
        
        if not recipients:
            # Get superuser emails as default recipients
            recipients = list(User.objects.filter(
                is_superuser=True, 
                email__isnull=False
            ).values_list('email', flat=True))
        
        if not recipients:
            logger.warning("No recipients found for alert notifications")
            return False
        
        # Group alerts by level for better organization
        critical_alerts = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        high_alerts = [a for a in alerts if a.level == AlertLevel.HIGH]
        medium_alerts = [a for a in alerts if a.level == AlertLevel.MEDIUM]
        
        # Create email content
        subject = f"Market Alert: {len(alerts)} alerts detected"
        if critical_alerts:
            subject = f"CRITICAL Market Alert: {len(critical_alerts)} critical issues"
        
        message_parts = [
            f"Market Intelligence Alert Summary - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 60,
            ""
        ]
        
        if critical_alerts:
            message_parts.extend([
                "🚨 CRITICAL ALERTS:",
                "-" * 20
            ])
            for alert in critical_alerts:
                message_parts.append(f"• {alert.title}: {alert.message}")
                message_parts.append(f"  Action: {alert.action_required}")
                message_parts.append("")
        
        if high_alerts:
            message_parts.extend([
                "⚠️  HIGH PRIORITY ALERTS:",
                "-" * 25
            ])
            for alert in high_alerts:
                message_parts.append(f"• {alert.title}: {alert.message}")
                message_parts.append(f"  Action: {alert.action_required}")
                message_parts.append("")
        
        if medium_alerts:
            message_parts.extend([
                "ℹ️  MEDIUM PRIORITY ALERTS:",
                "-" * 27
            ])
            for alert in medium_alerts[:5]:  # Limit to top 5 medium alerts
                message_parts.append(f"• {alert.title}: {alert.message}")
                message_parts.append("")
        
        message_parts.extend([
            "",
            "This is an automated alert from the Ubongo IQ Market Intelligence System.",
            "Log in to the admin panel for detailed analysis and data."
        ])
        
        message = "\n".join(message_parts)
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email='alerts@ubongo-iq.com',
                recipient_list=recipients,
                fail_silently=False
            )
            logger.info(f"Alert notifications sent to {len(recipients)} recipients")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send alert notifications: {e}")
            return False


# Convenience functions for external use
def run_market_monitoring() -> List[MarketAlert]:
    """Run market monitoring and return alerts."""
    alert_system = MarketAlertSystem()
    return alert_system.monitor_market_changes()


def send_market_alerts(recipients: Optional[List[str]] = None) -> bool:
    """Generate and send market alerts."""
    alert_system = MarketAlertSystem()
    alerts = alert_system.monitor_market_changes()
    
    if alerts:
        return alert_system.send_alert_notifications(alerts, recipients)
    
    return True
"""
Automated market intelligence analysis and reporting system.
"""
import statistics
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Any
from django.utils import timezone
from django.db.models import Avg, Count, Q
from blog.models_scraping import ScrapedData, ScrapingSource, TrendingTopic


class MarketIntelligenceAnalyzer:
    """Automated analysis of scraped B2B market data."""
    
    def __init__(self):
        self.data_cutoff = timezone.now() - timedelta(days=30)  # Last 30 days
        
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate a comprehensive market intelligence report."""
        recent_data = ScrapedData.objects.filter(scraped_at__gte=self.data_cutoff)
        
        report = {
            'generated_at': timezone.now(),
            'data_period': '30 days',
            'total_products': recent_data.count(),
            'pricing_analysis': self._analyze_pricing(recent_data),
            'supplier_intelligence': self._analyze_suppliers(recent_data),
            'logistics_insights': self._analyze_logistics(recent_data),
            'quality_metrics': self._analyze_quality(recent_data),
            'market_trends': self._analyze_trends(recent_data),
            'content_opportunities': self._identify_content_opportunities(recent_data),
            'alerts': self._generate_alerts(recent_data)
        }
        
        return report
    
    def _analyze_pricing(self, data) -> Dict[str, Any]:
        """Comprehensive pricing analysis."""
        # Extract pricing data from both new fields and raw_data
        pricing_data = []
        
        for item in data:
            price_info = {}
            
            # Try new fields first
            if hasattr(item, 'current_price') and item.current_price:
                price_info['current_price'] = float(item.current_price)
                price_info['original_price'] = float(item.original_price) if item.original_price else None
                price_info['discount'] = float(item.discount_percentage) if item.discount_percentage else 0
                price_info['bulk_tiers'] = len(item.bulk_pricing_tiers) if item.bulk_pricing_tiers else 0
            
            # Fall back to raw_data
            elif 'pricing' in item.raw_data:
                pricing = item.raw_data['pricing']
                price_info['current_price'] = pricing.get('current_price')
                price_info['original_price'] = pricing.get('original_price')
                price_info['discount'] = pricing.get('discount_percentage', 0)
                price_info['bulk_tiers'] = len(pricing.get('bulk_pricing_tiers', []))
            
            if price_info.get('current_price'):
                price_info['category'] = item.category
                pricing_data.append(price_info)
        
        if not pricing_data:
            return {'error': 'No pricing data available'}
        
        prices = [p['current_price'] for p in pricing_data]
        discounts = [p['discount'] for p in pricing_data if p['discount'] > 0]
        
        # Category analysis
        category_prices = defaultdict(list)
        for p in pricing_data:
            if p['category']:
                category_prices[p['category']].append(p['current_price'])
        
        category_averages = {
            cat: statistics.mean(prices) 
            for cat, prices in category_prices.items()
        }
        
        return {
            'total_products_with_pricing': len(pricing_data),
            'average_price': statistics.mean(prices),
            'median_price': statistics.median(prices),
            'price_range': {
                'min': min(prices),
                'max': max(prices)
            },
            'discount_analysis': {
                'products_with_discounts': len(discounts),
                'average_discount': statistics.mean(discounts) if discounts else 0,
                'discount_rate': len(discounts) / len(pricing_data) * 100
            },
            'bulk_pricing_availability': len([p for p in pricing_data if p['bulk_tiers'] > 0]),
            'category_pricing': dict(sorted(category_averages.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    def _analyze_suppliers(self, data) -> Dict[str, Any]:
        """Supplier landscape analysis."""
        supplier_data = []
        
        for item in data:
            supplier_info = {}
            
            # Try new fields first
            if hasattr(item, 'supplier_country') and item.supplier_country:
                supplier_info = {
                    'country': item.supplier_country,
                    'region': item.supplier_region,
                    'verification': item.verification_status,
                    'years': item.years_in_business,
                    'rating': item.supplier_rating
                }
            
            # Fall back to raw_data
            elif 'supplier' in item.raw_data:
                supplier = item.raw_data['supplier']
                supplier_info = {
                    'country': supplier.get('country'),
                    'region': supplier.get('region'),
                    'verification': supplier.get('verification_status'),
                    'years': supplier.get('years_in_business'),
                    'rating': supplier.get('rating')
                }
            
            if supplier_info.get('country'):
                supplier_data.append(supplier_info)
        
        if not supplier_data:
            return {'error': 'No supplier data available'}
        
        countries = Counter([s['country'] for s in supplier_data if s['country']])
        regions = Counter([s['region'] for s in supplier_data if s['region']])
        verified = len([s for s in supplier_data if s['verification'] == 'Verified'])
        
        years_data = [s['years'] for s in supplier_data if s['years'] and s['years'] > 0]
        ratings_data = [s['rating'] for s in supplier_data if s['rating'] and s['rating'] > 0]
        
        return {
            'total_suppliers': len(supplier_data),
            'geographic_distribution': {
                'by_country': dict(countries.most_common(10)),
                'by_region': dict(regions.most_common())
            },
            'verification_rate': verified / len(supplier_data) * 100,
            'experience_metrics': {
                'average_years': statistics.mean(years_data) if years_data else 0,
                'experienced_suppliers': len([y for y in years_data if y >= 10])
            },
            'quality_metrics': {
                'average_rating': statistics.mean(ratings_data) if ratings_data else 0,
                'high_rated_suppliers': len([r for r in ratings_data if r >= 4.5])
            }
        }
    
    def _analyze_logistics(self, data) -> Dict[str, Any]:
        """Logistics and shipping analysis."""
        logistics_data = []
        
        for item in data:
            logistics_info = {}
            
            # Try new fields first
            if hasattr(item, 'minimum_order_quantity') and item.minimum_order_quantity:
                logistics_info = {
                    'moq': item.minimum_order_quantity,
                    'lead_time': item.lead_time_days,
                    'shipping_cost': float(item.shipping_cost) if item.shipping_cost else None,
                    'shipping_methods': item.shipping_methods or []
                }
            
            # Fall back to raw_data
            elif 'logistics' in item.raw_data:
                logistics = item.raw_data['logistics']
                logistics_info = {
                    'moq': logistics.get('moq'),
                    'lead_time': logistics.get('lead_time_days'),
                    'shipping_cost': logistics.get('shipping_cost'),
                    'shipping_methods': logistics.get('shipping_methods', [])
                }
            
            if logistics_info.get('moq'):
                logistics_data.append(logistics_info)
        
        if not logistics_data:
            return {'error': 'No logistics data available'}
        
        moqs = [l['moq'] for l in logistics_data if l['moq']]
        lead_times = [l['lead_time'] for l in logistics_data if l['lead_time']]
        shipping_costs = [l['shipping_cost'] for l in logistics_data if l['shipping_cost']]
        
        # MOQ categories
        moq_categories = {
            'small_business_friendly': len([m for m in moqs if m <= 100]),
            'medium_orders': len([m for m in moqs if 101 <= m <= 500]),
            'large_orders': len([m for m in moqs if m > 500])
        }
        
        return {
            'moq_analysis': {
                'average': statistics.mean(moqs) if moqs else 0,
                'median': statistics.median(moqs) if moqs else 0,
                'range': {'min': min(moqs), 'max': max(moqs)} if moqs else {},
                'categories': moq_categories
            },
            'lead_time_analysis': {
                'average_days': statistics.mean(lead_times) if lead_times else 0,
                'fast_delivery': len([l for l in lead_times if l <= 7]),
                'standard_delivery': len([l for l in lead_times if 8 <= l <= 21]),
                'slow_delivery': len([l for l in lead_times if l > 21])
            },
            'shipping_cost_analysis': {
                'average_cost': statistics.mean(shipping_costs) if shipping_costs else 0,
                'cost_range': {'min': min(shipping_costs), 'max': max(shipping_costs)} if shipping_costs else {}
            }
        }
    
    def _analyze_quality(self, data) -> Dict[str, Any]:
        """Quality and certification analysis."""
        quality_data = []
        all_certifications = set()
        
        for item in data:
            quality_info = {}
            
            # Try new fields first
            if hasattr(item, 'rating') and item.rating:
                quality_info = {
                    'rating': item.rating,
                    'rating_count': item.rating_count,
                    'certifications': item.certifications or []
                }
            
            # Fall back to raw_data
            elif 'quality' in item.raw_data:
                quality = item.raw_data['quality']
                quality_info = {
                    'rating': quality.get('rating'),
                    'rating_count': quality.get('rating_count'),
                    'certifications': quality.get('certifications', [])
                }
            
            if quality_info.get('rating'):
                quality_data.append(quality_info)
                all_certifications.update(quality_info.get('certifications', []))
        
        if not quality_data:
            return {'error': 'No quality data available'}
        
        ratings = [q['rating'] for q in quality_data if q['rating']]
        
        return {
            'rating_analysis': {
                'average_rating': statistics.mean(ratings),
                'high_quality': len([r for r in ratings if r >= 4.5]),
                'good_quality': len([r for r in ratings if 4.0 <= r < 4.5]),
                'fair_quality': len([r for r in ratings if r < 4.0])
            },
            'certification_landscape': {
                'total_certifications': len(all_certifications),
                'common_certifications': list(all_certifications)[:10],
                'certified_products': len([q for q in quality_data if q.get('certifications')])
            }
        }
    
    def _analyze_trends(self, data) -> Dict[str, Any]:
        """Market trend analysis."""
        trend_data = []
        
        for item in data:
            trend_info = {}
            
            # Try new fields first
            if hasattr(item, 'price_trend'):
                trend_info = {
                    'price_trend': item.price_trend,
                    'seasonal_demand': item.seasonal_demand,
                    'views': item.views,
                    'sales': item.sales,
                    'category': item.category
                }
            
            # Fall back to raw_data
            elif 'market_intelligence' in item.raw_data:
                market = item.raw_data['market_intelligence']
                trend_info = {
                    'price_trend': market.get('price_trend'),
                    'seasonal_demand': market.get('seasonal_demand'),
                    'views': market.get('views'),
                    'sales': market.get('sales'),
                    'category': item.category
                }
            
            if trend_info.get('category'):
                trend_data.append(trend_info)
        
        price_trends = Counter([t['price_trend'] for t in trend_data if t['price_trend']])
        seasonal_patterns = Counter([t['seasonal_demand'] for t in trend_data if t['seasonal_demand']])
        category_performance = defaultdict(list)
        
        for t in trend_data:
            if t.get('views') and t.get('category'):
                category_performance[t['category']].append(t['views'])
        
        top_categories = {
            cat: statistics.mean(views) 
            for cat, views in category_performance.items()
        }
        
        return {
            'price_movements': dict(price_trends),
            'seasonal_patterns': dict(seasonal_patterns),
            'top_performing_categories': dict(sorted(top_categories.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    def _identify_content_opportunities(self, data) -> List[Dict[str, Any]]:
        """Identify high-value content opportunities."""
        opportunities = []
        
        # Get analysis results
        pricing = self._analyze_pricing(data)
        suppliers = self._analyze_suppliers(data)
        logistics = self._analyze_logistics(data)
        
        # Generate content ideas based on data
        if 'category_pricing' in pricing:
            for category, avg_price in list(pricing['category_pricing'].items())[:3]:
                opportunities.append({
                    'type': 'price_analysis',
                    'title': f"Price Analysis: {category.replace('-', ' ').title()} Market Trends",
                    'data_points': f"${avg_price:.2f} average price analysis",
                    'value_score': 8
                })
        
        if 'geographic_distribution' in suppliers:
            top_country = list(suppliers['geographic_distribution']['by_country'].keys())[0]
            opportunities.append({
                'type': 'supplier_guide',
                'title': f"Supplier Guide: Why {top_country} Dominates B2B Manufacturing",
                'data_points': f"{suppliers['total_suppliers']} suppliers analyzed",
                'value_score': 9
            })
        
        if 'moq_analysis' in logistics:
            avg_moq = logistics['moq_analysis']['average']
            opportunities.append({
                'type': 'procurement_guide',
                'title': f"MOQ Strategy: Optimizing Orders from {avg_moq:.0f} Unit Minimums",
                'data_points': f"MOQ range analysis with cost optimization",
                'value_score': 7
            })
        
        return sorted(opportunities, key=lambda x: x['value_score'], reverse=True)
    
    def _generate_alerts(self, data) -> List[Dict[str, Any]]:
        """Generate market alerts based on data analysis."""
        alerts = []
        
        # Price trend alerts
        rising_prices = data.filter(
            Q(price_trend='Rising') | 
            Q(raw_data__market_intelligence__price_trend='Rising')
        ).count()
        
        if rising_prices > data.count() * 0.3:  # More than 30% rising
            alerts.append({
                'type': 'price_alert',
                'level': 'warning',
                'message': f"Price increases detected in {rising_prices} products",
                'action': 'Consider accelerating procurement decisions'
            })
        
        # Supplier verification alert
        if hasattr(data.first(), 'verification_status'):
            unverified = data.exclude(verification_status='Verified').count()
        else:
            unverified = data.exclude(raw_data__supplier__verification_status='Verified').count()
        
        if unverified > data.count() * 0.4:  # More than 40% unverified
            alerts.append({
                'type': 'supplier_alert',
                'level': 'info',
                'message': f"{unverified} products from unverified suppliers",
                'action': 'Review supplier verification requirements'
            })
        
        return alerts


def run_automated_analysis():
    """Run the automated analysis and return results."""
    analyzer = MarketIntelligenceAnalyzer()
    return analyzer.generate_comprehensive_report()
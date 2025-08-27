"""
Celery tasks for web scraping and data-driven content generation.
"""
import logging
from datetime import timedelta
from typing import List, Dict, Any

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User

from blog.models_scraping import (
    ScrapingSource, ScrapedData, TrendingTopic, 
    ScrapingLog, ContentGenerationQueue
)
from blog.models_ai import ContentGenerationRequest
from blog.models import Category
from utils.scrapers import ScraperFactory
from utils.ai_client import ai_client

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scrape_website(self, source_id: int):
    """Scrape a specific website and store the data."""
    try:
        source = ScrapingSource.objects.get(id=source_id, enabled=True)
    except ScrapingSource.DoesNotExist:
        logger.error(f"Scraping source {source_id} not found or disabled")
        return {'error': 'Source not found'}
    
    # Create scraping log
    log = ScrapingLog.objects.create(
        source=source,
        status='started'
    )
    
    try:
        # Create scraper instance
        scraper = ScraperFactory.create_scraper(source)
        if not scraper:
            raise Exception(f"No scraper available for {source.website}")
        
        logger.info(f"Starting scrape of {source.name}")
        
        # Perform scraping
        scraping_results = scraper.scrape()
        
        # Process results
        items_new = 0
        items_updated = 0
        items_failed = 0
        
        for item_data in scraping_results.get('items', []):
            try:
                result = process_scraped_item(source, item_data)
                if result['created']:
                    items_new += 1
                else:
                    items_updated += 1
                    
            except Exception as e:
                logger.error(f"Error processing scraped item: {e}")
                items_failed += 1
        
        # Update scraping source
        source.last_scraped = timezone.now()
        source.last_success = timezone.now()
        source.consecutive_failures = 0
        source.save()
        
        # Update log
        log.status = 'success' if items_failed == 0 else 'partial'
        log.completed_at = timezone.now()
        log.duration_seconds = (log.completed_at - log.started_at).seconds
        log.items_found = len(scraping_results.get('items', []))
        log.items_new = items_new
        log.items_updated = items_updated
        log.items_failed = items_failed
        log.notes = f"Errors: {len(scraping_results.get('errors', []))}"
        log.save()
        
        # Trigger trend analysis
        analyze_trends.delay(source_id)
        
        logger.info(f"Scraping completed: {items_new} new, {items_updated} updated, {items_failed} failed")
        
        return {
            'success': True,
            'items_new': items_new,
            'items_updated': items_updated,
            'items_failed': items_failed,
            'duration': log.duration_seconds
        }
        
    except Exception as e:
        logger.error(f"Scraping failed for {source.name}: {e}")
        
        # Update failure tracking
        source.consecutive_failures += 1
        source.save()
        
        # Update log
        log.status = 'failed'
        log.completed_at = timezone.now()
        log.error_message = str(e)
        log.save()
        
        # Retry task if not exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying scraping task in 10 minutes (retry {self.request.retries + 1})")
            raise self.retry(countdown=600)  # Retry in 10 minutes
        
        return {'error': str(e)}


def process_scraped_item(source: ScrapingSource, item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process and store a comprehensive scraped item with enhanced data."""
    with transaction.atomic():
        # Try to get existing item
        scraped_item, created = ScrapedData.objects.get_or_create(
            source=source,
            external_id=item_data['external_id'],
            defaults={
                # Basic info
                'url': item_data.get('url', ''),
                'title': item_data.get('title', '')[:500],
                'description': item_data.get('description', ''),
                'category': item_data.get('category', '')[:200],
                'tags': item_data.get('tags', '')[:500],
                
                # Enhanced pricing data
                'current_price': item_data.get('current_price'),
                'original_price': item_data.get('original_price'),
                'discount_percentage': item_data.get('discount_percentage'),
                'price_currency': item_data.get('price_currency', 'USD'),
                'bulk_pricing_tiers': item_data.get('bulk_pricing_tiers', []),
                
                # Order specifications
                'minimum_order_quantity': item_data.get('minimum_order_quantity'),
                'order_units': item_data.get('order_units', ''),
                'lead_time_days': item_data.get('lead_time_days'),
                
                # Product specifications
                'material': item_data.get('material', ''),
                'dimensions': item_data.get('dimensions', ''),
                'certifications': item_data.get('certifications', []),
                'quality_standards': item_data.get('quality_standards', []),
                'color_options': item_data.get('color_options', []),
                'product_features': item_data.get('product_features', []),
                
                # Customer feedback
                'rating': item_data.get('rating'),
                'rating_count': item_data.get('rating_count'),
                'review_highlights': item_data.get('review_highlights', []),
                'common_complaints': item_data.get('common_complaints', []),
                
                # Supplier data
                'supplier_name': item_data.get('supplier_name', ''),
                'supplier_location': item_data.get('supplier_location', ''),
                'supplier_country': item_data.get('supplier_country', ''),
                'supplier_region': item_data.get('supplier_region', ''),
                'years_in_business': item_data.get('years_in_business'),
                'verification_status': item_data.get('verification_status', ''),
                'supplier_certifications': item_data.get('supplier_certifications', []),
                'response_rate': item_data.get('response_rate'),
                'supplier_rating': item_data.get('supplier_rating'),
                
                # Market intelligence
                'views': item_data.get('views'),
                'likes': item_data.get('likes'),
                'sales': item_data.get('sales'),
                'recent_orders': item_data.get('recent_orders'),
                'trending_rank': item_data.get('trending_rank'),
                'search_keywords': item_data.get('search_keywords', []),
                'seasonal_demand': item_data.get('seasonal_demand', ''),
                'price_trend': item_data.get('price_trend', ''),
                
                # Logistics
                'shipping_cost': item_data.get('shipping_cost'),
                'shipping_methods': item_data.get('shipping_methods', []),
                'port_of_shipment': item_data.get('port_of_shipment', ''),
                
                # Media
                'image_urls': item_data.get('image_urls', []),
                'video_urls': item_data.get('video_urls', []),
                
                # Raw metadata
                'raw_data': item_data.get('raw_data', {}),
            }
        )
        
        if not created:
            # Update existing item with new data
            for field in ['title', 'description', 'category', 'tags', 'current_price', 'original_price', 
                         'rating', 'rating_count', 'views', 'sales', 'recent_orders', 'trending_rank',
                         'seasonal_demand', 'price_trend', 'shipping_cost']:
                if field in item_data:
                    value = item_data[field]
                    if field in ['title', 'description', 'category', 'tags'] and value:
                        value = str(value)[:500 if field in ['title', 'description'] else 200]
                    setattr(scraped_item, field, value)
            
            # Update JSON fields
            for json_field in ['bulk_pricing_tiers', 'certifications', 'quality_standards', 
                              'color_options', 'product_features', 'review_highlights', 
                              'common_complaints', 'supplier_certifications', 'search_keywords',
                              'shipping_methods', 'image_urls', 'video_urls']:
                if json_field in item_data:
                    setattr(scraped_item, json_field, item_data[json_field])
            
            scraped_item.raw_data.update(item_data.get('raw_data', {}))
            scraped_item.save()
        
        return {
            'created': created,
            'item_id': scraped_item.id
        }


@shared_task
def analyze_trends(source_id: int):
    """Analyze scraped data to identify trending topics."""
    try:
        source = ScrapingSource.objects.get(id=source_id)
    except ScrapingSource.DoesNotExist:
        logger.error(f"Source {source_id} not found for trend analysis")
        return
    
    # Get recent scraped data (last 7 days)
    recent_cutoff = timezone.now() - timedelta(days=7)
    recent_items = ScrapedData.objects.filter(
        source=source,
        scraped_at__gte=recent_cutoff
    )
    
    # Group by category and analyze trends
    category_trends = {}
    
    for item in recent_items:
        category = item.category or 'uncategorized'
        
        if category not in category_trends:
            category_trends[category] = {
                'frequency': 0,
                'total_views': 0,
                'items': [],
                'keywords': {}
            }
        
        category_trends[category]['frequency'] += 1
        category_trends[category]['total_views'] += item.views or 0
        category_trends[category]['items'].append({
            'id': item.id,
            'title': item.title,
            'url': item.url,
            'price': item.price
        })
        
        # Extract keywords from title and tags
        keywords = extract_keywords(item.title + ' ' + item.tags)
        for keyword in keywords:
            if keyword in category_trends[category]['keywords']:
                category_trends[category]['keywords'][keyword] += 1
            else:
                category_trends[category]['keywords'][keyword] = 1
    
    # Create or update TrendingTopic records
    for category, trend_data in category_trends.items():
        if trend_data['frequency'] >= 3:  # Minimum threshold
            # Find most popular keywords for this category
            top_keywords = sorted(
                trend_data['keywords'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            
            for keyword, frequency in top_keywords:
                trending_topic, created = TrendingTopic.objects.get_or_create(
                    source=source,
                    topic=keyword,
                    category=category,
                    defaults={
                        'frequency': frequency,
                        'total_views': trend_data['total_views'],
                        'sample_items': trend_data['items'][:5]
                    }
                )
                
                if not created:
                    trending_topic.frequency = frequency
                    trending_topic.total_views = trend_data['total_views']
                    trending_topic.sample_items = trend_data['items'][:5]
                    trending_topic.save()
    
    # Queue content generation for top trends
    queue_trending_content.delay(source_id)
    
    logger.info(f"Trend analysis completed for {source.name}: {len(category_trends)} categories analyzed")


def extract_keywords(text: str) -> List[str]:
    """Extract relevant keywords from text."""
    import re
    
    # Simple keyword extraction - can be enhanced with NLP libraries
    text = text.lower()
    
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'is', 'are', 'was', 
        'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 
        'did', 'will', 'would', 'could', 'should'
    }
    
    # Extract words (2+ characters, alphanumeric)
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    
    # Filter out stop words and return unique keywords
    keywords = [word for word in words if word not in stop_words]
    
    return list(set(keywords))


@shared_task
def queue_trending_content(source_id: int):
    """Queue content generation for trending topics."""
    try:
        source = ScrapingSource.objects.get(id=source_id)
    except ScrapingSource.DoesNotExist:
        return
    
    # Get top trending topics that don't have content generated yet
    trending_topics = TrendingTopic.objects.filter(
        source=source,
        content_generated=False
    ).order_by('-trending_score')[:5]
    
    # Get default category for content generation
    try:
        default_category = Category.objects.get(slug='tech')
    except Category.DoesNotExist:
        default_category = Category.objects.first()
        if not default_category:
            logger.error("No categories found for content generation")
            return
    
    for topic in trending_topics:
        # Create content generation queue item
        ContentGenerationQueue.objects.get_or_create(
            trending_topic=topic,
            target_category=default_category,
            defaults={
                'content_type': 'trend_analysis',
                'title': f"Market Analysis: {topic.topic.title()} Trends",
                'priority': 'normal',
                'context_data': {
                    'source': source.name,
                    'frequency': topic.frequency,
                    'sample_items': topic.sample_items[:3]
                }
            }
        )
    
    # Process queued content generation
    process_content_queue.delay()


@shared_task
def process_content_queue():
    """Process queued content generation requests."""
    # Get unprocessed items from queue
    queue_items = ContentGenerationQueue.objects.filter(
        processed=False
    ).order_by('-priority', 'scheduled_for')[:3]  # Process 3 at a time
    
    for queue_item in queue_items:
        try:
            generate_content_from_data.delay(queue_item.id)
            queue_item.processed = True
            queue_item.save()
            
        except Exception as e:
            logger.error(f"Error queuing content generation: {e}")


@shared_task
def generate_content_from_data(queue_item_id: int):
    """Generate content from scraped data using AI."""
    try:
        queue_item = ContentGenerationQueue.objects.get(id=queue_item_id)
    except ContentGenerationQueue.DoesNotExist:
        logger.error(f"Content queue item {queue_item_id} not found")
        return
    
    try:
        # Get system user for content generation
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            logger.error("No superuser found for content generation")
            return
        
        # Create content generation request
        content_request = ContentGenerationRequest.objects.create(
            topic=queue_item.title,
            category=queue_item.target_category,
            status='generating',
            model_used=ai_client.model,
            requested_by=user,
            generation_started_at=timezone.now(),
            prompt_used=f"Data-driven content for: {queue_item.content_type}"
        )
        
        # Generate content using AI with scraped data context
        context_data = queue_item.context_data
        
        # Create enhanced prompt with scraped data
        enhanced_prompt = create_data_driven_prompt(queue_item)
        
        # Generate outline
        outline = ai_client.generate_text(enhanced_prompt['outline'], max_tokens=800)
        if outline:
            content_request.generated_outline = outline
            content_request.save()
            
            # Generate full content
            content = ai_client.generate_text(enhanced_prompt['content'].format(outline=outline), max_tokens=1500)
            if content:
                content_request.generated_content = content
                content_request.word_count = len(content.split())
                
                # Generate title and meta description
                title = ai_client.generate_seo_title(content)
                if title:
                    content_request.generated_title = title.strip().strip('"')
                
                meta_desc = ai_client.generate_meta_description(content)
                if meta_desc:
                    content_request.generated_meta_description = meta_desc.strip().strip('"')
                
                content_request.status = 'review'
                content_request.generation_completed_at = timezone.now()
                content_request.save()
                
                # Update queue item and trending topic
                queue_item.content_request = content_request
                queue_item.save()
                
                if queue_item.trending_topic:
                    queue_item.trending_topic.content_generated = True
                    queue_item.trending_topic.content_generation_request = content_request
                    queue_item.trending_topic.save()
                
                logger.info(f"Generated content for: {queue_item.title}")
                
            else:
                content_request.status = 'failed'
                content_request.save()
        else:
            content_request.status = 'failed'
            content_request.save()
            
    except Exception as e:
        logger.error(f"Content generation failed for queue item {queue_item_id}: {e}")


def create_data_driven_prompt(queue_item: ContentGenerationQueue) -> Dict[str, str]:
    """Create AI prompts enhanced with scraped data."""
    context = queue_item.context_data
    content_type = queue_item.get_content_type_display()
    
    # Base context from scraped data
    data_context = f"""
    Based on market data from {context.get('source', 'various sources')}:
    - Topic: {queue_item.title}
    - Frequency: {context.get('frequency', 'N/A')} occurrences
    - Sample products/items: {context.get('sample_items', [])}
    """
    
    prompts = {
        'outline': f"""Create an article outline for: {queue_item.title}
        
        {data_context}
        
        Content type: {content_type}
        Format:
        1. Title
        2. Introduction
        3. 3-4 main sections based on the market data
        4. Conclusion with insights
        """,
        
        'content': """Write a comprehensive article based on this outline and market data:
        
        {outline}
        
        Requirements:
        - Use the market data to provide real insights
        - Professional, informative tone
        - 700-900 words
        - Include actionable insights
        - Use markdown formatting
        """
    }
    
    return prompts


@shared_task
def periodic_scraping_scheduler():
    """Schedule scraping tasks for all enabled sources that are due."""
    from django.db import models
    
    sources_due = ScrapingSource.objects.filter(
        enabled=True
    ).filter(
        models.Q(last_scraped__isnull=True) |
        models.Q(last_scraped__lt=timezone.now() - models.F('scrape_frequency_hours') * timedelta(hours=1))
    )
    
    for source in sources_due:
        if source.is_healthy:  # Only scrape healthy sources
            scrape_website.delay(source.id)
            logger.info(f"Scheduled scraping for {source.name}")
    
    return f"Scheduled scraping for {sources_due.count()} sources"
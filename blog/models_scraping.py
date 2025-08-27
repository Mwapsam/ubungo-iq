"""
Models for web scraping and data-driven content generation.
"""
import json
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel, MultiFieldPanel


@register_snippet
class ScrapingSource(models.Model):
    """Configuration for different scraping sources."""

    WEBSITE_CHOICES = [
        ('alibaba', 'Alibaba B2B'),
        ('globaltrade', 'GlobalTrade.net'),
        ('etsy', 'Etsy'),
    ]

    name = models.CharField(max_length=100)
    website = models.CharField(max_length=20, choices=WEBSITE_CHOICES, unique=True)
    base_url = models.URLField()

    # Scraping configuration
    enabled = models.BooleanField(default=True)
    scrape_frequency_hours = models.IntegerField(default=24, help_text="How often to scrape (in hours)")
    max_items_per_scrape = models.IntegerField(default=50)

    # Request settings
    request_delay_seconds = models.FloatField(default=2.0, help_text="Delay between requests")
    user_agent = models.CharField(
        max_length=300, 
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    # Selectors and configuration (JSON)
    scraping_config = models.JSONField(default=dict, help_text="CSS selectors and scraping rules")

    # Status
    last_scraped = models.DateTimeField(null=True, blank=True)
    last_success = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        MultiFieldPanel([
            FieldPanel('name'),
            FieldPanel('website'),
            FieldPanel('base_url'),
            FieldPanel('enabled'),
        ], heading='Basic Information'),
        
        MultiFieldPanel([
            FieldPanel('scrape_frequency_hours'),
            FieldPanel('max_items_per_scrape'),
            FieldPanel('request_delay_seconds'),
            FieldPanel('user_agent'),
            FieldPanel('scraping_config'),
        ], heading='Scraping Configuration'),
        
        MultiFieldPanel([
            FieldPanel('last_scraped'),
            FieldPanel('last_success'),
            FieldPanel('consecutive_failures'),
        ], heading='Status Information'),
    ]
    
    class Meta:
        verbose_name = "Scraping Source"
        verbose_name_plural = "Scraping Sources"

    def __str__(self):
        return f"{self.name} ({self.get_website_display()})"

    @property
    def is_due_for_scraping(self):
        """Check if this source is due for scraping."""
        if not self.enabled or not self.last_scraped:
            return True

        next_scrape = self.last_scraped + timedelta(hours=self.scrape_frequency_hours)
        return timezone.now() >= next_scrape

    @property
    def is_healthy(self):
        """Check if scraping source is healthy (low failure rate)."""
        return self.consecutive_failures < 5


@register_snippet
class ScrapedData(models.Model):
    """Enhanced scraped data with detailed product and market intelligence."""

    source = models.ForeignKey(ScrapingSource, on_delete=models.CASCADE, related_name='scraped_items')

    # Item identification
    external_id = models.CharField(max_length=200, help_text="ID from the source website")
    url = models.URLField()
    title = models.CharField(max_length=500)

    # Basic content data
    description = models.TextField(blank=True)
    category = models.CharField(max_length=200, blank=True)
    tags = models.CharField(max_length=500, blank=True)

    # === 1. ENHANCED PRODUCT-LEVEL DATA ===
    
    # Pricing data
    current_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    original_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    price_currency = models.CharField(max_length=10, default='USD')
    bulk_pricing_tiers = models.JSONField(default=list, help_text="List of quantity-price tiers")
    
    # Order specifications
    minimum_order_quantity = models.IntegerField(null=True, blank=True, help_text="MOQ")
    order_units = models.CharField(max_length=50, blank=True, help_text="pieces, kg, meters, etc.")
    lead_time_days = models.IntegerField(null=True, blank=True)
    
    # Product specifications
    material = models.CharField(max_length=200, blank=True)
    dimensions = models.CharField(max_length=200, blank=True, help_text="Size, weight, etc.")
    certifications = models.JSONField(default=list, help_text="CE, ISO, FDA, etc.")
    quality_standards = models.JSONField(default=list, help_text="Standards compliance")
    color_options = models.JSONField(default=list, help_text="Available colors")
    
    # Customer feedback
    rating = models.FloatField(null=True, blank=True)
    rating_count = models.IntegerField(null=True, blank=True)
    review_highlights = models.JSONField(default=list, help_text="Key review points")
    common_complaints = models.JSONField(default=list, help_text="Frequent issues mentioned")

    # === 2. SELLER/MANUFACTURER DATA ===
    
    supplier_name = models.CharField(max_length=300, blank=True)
    supplier_location = models.CharField(max_length=200, blank=True)
    supplier_country = models.CharField(max_length=100, blank=True)
    supplier_region = models.CharField(max_length=100, blank=True, help_text="Asia, Europe, etc.")
    years_in_business = models.IntegerField(null=True, blank=True)
    verification_status = models.CharField(max_length=100, blank=True, help_text="Gold, Verified, etc.")
    supplier_certifications = models.JSONField(default=list, help_text="ISO9001, etc.")
    response_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    supplier_rating = models.FloatField(null=True, blank=True)

    # === 3. MARKET INTELLIGENCE ===
    
    # Trending data
    views = models.IntegerField(null=True, blank=True)
    likes = models.IntegerField(null=True, blank=True)
    sales = models.IntegerField(null=True, blank=True)
    recent_orders = models.IntegerField(null=True, blank=True)
    trending_rank = models.IntegerField(null=True, blank=True)
    
    # Keyword data
    search_keywords = models.JSONField(default=list, help_text="SEO keywords from listing")
    product_features = models.JSONField(default=list, help_text="Key features listed")
    
    # Shipping & logistics
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipping_methods = models.JSONField(default=list, help_text="Air, sea, express, etc.")
    port_of_shipment = models.CharField(max_length=200, blank=True)
    
    # Visual content
    image_urls = models.JSONField(default=list, help_text="Product image URLs")
    video_urls = models.JSONField(default=list, help_text="Product video URLs")
    
    # Seasonal data
    seasonal_demand = models.CharField(max_length=100, blank=True, help_text="High/Low season")
    price_trend = models.CharField(max_length=20, blank=True, help_text="Rising/Falling/Stable")
    
    # Raw metadata
    raw_data = models.JSONField(default=dict, help_text="Full scraped data")

    # Content generation tracking
    content_generated = models.BooleanField(default=False)
    content_generation_request = models.ForeignKey(
        'blog.ContentGenerationRequest',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )

    # Timestamps
    scraped_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['source', 'external_id']
        ordering = ['-scraped_at']
        indexes = [
            models.Index(fields=['source', 'content_generated']),
            models.Index(fields=['scraped_at']),
            models.Index(fields=['category']),
        ]

    panels = [
        MultiFieldPanel([
            FieldPanel('source'),
            FieldPanel('title'),
            FieldPanel('url'),
            FieldPanel('external_id'),
            FieldPanel('category'),
        ], heading='Basic Information'),
        
        MultiFieldPanel([
            FieldPanel('current_price'),
            FieldPanel('original_price'),
            FieldPanel('discount_percentage'),
            FieldPanel('price_currency'),
            FieldPanel('bulk_pricing_tiers'),
            FieldPanel('minimum_order_quantity'),
            FieldPanel('order_units'),
            FieldPanel('lead_time_days'),
        ], heading='Pricing & Order Details'),
        
        MultiFieldPanel([
            FieldPanel('material'),
            FieldPanel('dimensions'),
            FieldPanel('certifications'),
            FieldPanel('quality_standards'),
            FieldPanel('color_options'),
            FieldPanel('product_features'),
        ], heading='Product Specifications'),
        
        MultiFieldPanel([
            FieldPanel('rating'),
            FieldPanel('rating_count'),
            FieldPanel('review_highlights'),
            FieldPanel('common_complaints'),
        ], heading='Customer Feedback'),
        
        MultiFieldPanel([
            FieldPanel('supplier_name'),
            FieldPanel('supplier_location'),
            FieldPanel('supplier_country'),
            FieldPanel('supplier_region'),
            FieldPanel('years_in_business'),
            FieldPanel('verification_status'),
            FieldPanel('supplier_certifications'),
            FieldPanel('response_rate'),
            FieldPanel('supplier_rating'),
        ], heading='Supplier Information'),
        
        MultiFieldPanel([
            FieldPanel('views'),
            FieldPanel('sales'),
            FieldPanel('recent_orders'),
            FieldPanel('trending_rank'),
            FieldPanel('search_keywords'),
            FieldPanel('seasonal_demand'),
            FieldPanel('price_trend'),
        ], heading='Market Intelligence'),
        
        MultiFieldPanel([
            FieldPanel('shipping_cost'),
            FieldPanel('shipping_methods'),
            FieldPanel('port_of_shipment'),
        ], heading='Logistics'),
        
        MultiFieldPanel([
            FieldPanel('image_urls'),
            FieldPanel('video_urls'),
        ], heading='Media'),
        
        MultiFieldPanel([
            FieldPanel('content_generated'),
            FieldPanel('content_generation_request'),
        ], heading='Content Generation'),
        
        FieldPanel('raw_data'),
    ]

    def __str__(self):
        return f"{self.title} ({self.source.website})"

    @property
    def is_trending(self):
        """Enhanced trending calculation with multiple factors."""
        factors = []
        
        # View metrics
        if self.views and self.views > 100:
            factors.append(self.views / 100)
        
        # Sales activity
        if self.sales:
            factors.append(self.sales * 5)
        if self.recent_orders:
            factors.append(self.recent_orders * 3)
            
        # Rating quality
        if self.rating and self.rating >= 4.0:
            factors.append(2)
            
        # Trending rank (lower is better)
        if self.trending_rank and self.trending_rank <= 100:
            factors.append((101 - self.trending_rank) / 20)
            
        return sum(factors) > 10

    @property 
    def discount_amount(self):
        """Calculate discount amount if both prices available."""
        if self.original_price and self.current_price:
            return self.original_price - self.current_price
        return None

    @property
    def has_bulk_pricing(self):
        """Check if product offers bulk pricing."""
        return bool(self.bulk_pricing_tiers)

    @property
    def is_verified_supplier(self):
        """Check if supplier has verification status."""
        return bool(self.verification_status)

    @property
    def content_generation_value(self):
        """Calculate how valuable this item is for content generation."""
        score = 0
        
        # High ratings = good for reviews
        if self.rating and self.rating >= 4.5:
            score += 3
        
        # Many reviews = good data
        if self.rating_count and self.rating_count >= 50:
            score += 2
            
        # Verified supplier = trustworthy
        if self.is_verified_supplier:
            score += 2
            
        # Certifications = compliance articles
        if self.certifications:
            score += len(self.certifications)
            
        # Bulk pricing = business guides
        if self.has_bulk_pricing:
            score += 2
            
        # Trending = market analysis
        if self.is_trending:
            score += 3
            
        return score

    @property
    def regional_insights(self):
        """Generate regional market insights."""
        insights = []
        
        if self.supplier_country:
            insights.append(f"Sourced from {self.supplier_country}")
            
        if self.supplier_region and self.shipping_cost:
            insights.append(f"{self.supplier_region} supplier with ${self.shipping_cost} shipping")
            
        if self.port_of_shipment:
            insights.append(f"Ships from {self.port_of_shipment}")
            
        return insights


@register_snippet
class TrendingTopic(models.Model):
    """Aggregated trending topics from scraped data."""

    source = models.ForeignKey(ScrapingSource, on_delete=models.CASCADE)
    topic = models.CharField(max_length=200)
    category = models.CharField(max_length=200, blank=True)

    # Trend metrics
    frequency = models.IntegerField(default=1, help_text="How often this topic appears")
    total_views = models.BigIntegerField(default=0)
    total_sales = models.BigIntegerField(default=0)
    average_rating = models.FloatField(null=True, blank=True)

    # Related items
    sample_items = models.JSONField(default=list, help_text="Sample scraped items for this topic")

    # Content generation
    content_generated = models.BooleanField(default=False)
    content_generation_request = models.ForeignKey(
        'blog.ContentGenerationRequest',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )

    # Time tracking
    first_seen = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['source', 'topic', 'category']
        ordering = ['-frequency', '-total_views']

    panels = [
        MultiFieldPanel([
            FieldPanel('source'),
            FieldPanel('topic'),
            FieldPanel('category'),
        ], heading='Topic Information'),
        
        MultiFieldPanel([
            FieldPanel('frequency'),
            FieldPanel('total_views'),
            FieldPanel('total_sales'),
            FieldPanel('average_rating'),
        ], heading='Trend Metrics'),
        
        MultiFieldPanel([
            FieldPanel('content_generated'),
            FieldPanel('content_generation_request'),
        ], heading='Content Generation'),
        
        FieldPanel('sample_items'),
    ]

    def __str__(self):
        return f"{self.topic} ({self.frequency} items)"

    @property
    def trending_score(self):
        """Calculate trending score for ranking."""
        recency_bonus = 1.0
        if self.last_updated:
            days_old = (timezone.now() - self.last_updated).days
            recency_bonus = max(0.1, 1.0 - (days_old * 0.1))

        return (self.frequency * self.total_views * recency_bonus) / 1000


@register_snippet
class ScrapingLog(models.Model):
    """Log scraping activities and results."""

    STATUS_CHOICES = [
        ('started', 'Started'),
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
    ]

    source = models.ForeignKey(ScrapingSource, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    # Results
    items_found = models.IntegerField(default=0)
    items_new = models.IntegerField(default=0)
    items_updated = models.IntegerField(default=0)
    items_failed = models.IntegerField(default=0)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)

    # Additional info
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    panels = [
        MultiFieldPanel([
            FieldPanel('source'),
            FieldPanel('status'),
        ], heading='Basic Information'),
        
        MultiFieldPanel([
            FieldPanel('items_found'),
            FieldPanel('items_new'),
            FieldPanel('items_updated'),
            FieldPanel('items_failed'),
        ], heading='Results'),
        
        MultiFieldPanel([
            FieldPanel('error_message'),
            FieldPanel('error_traceback'),
            FieldPanel('notes'),
        ], heading='Error Information'),
    ]

    def __str__(self):
        return f"{self.source.name} - {self.get_status_display()} ({self.started_at})"


@register_snippet
class ContentGenerationQueue(models.Model):
    """Queue for generating content from scraped data."""
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    TYPE_CHOICES = [
        ('product_review', 'Product Review'),
        ('trend_analysis', 'Trend Analysis'),
        ('market_insights', 'Market Insights'),
        ('buyer_guide', 'Buyer Guide'),
        ('price_comparison', 'Price Comparison'),
    ]
    
    # Content details
    content_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Data sources
    scraped_items = models.ManyToManyField(ScrapedData, blank=True)
    trending_topic = models.ForeignKey(TrendingTopic, null=True, blank=True, on_delete=models.CASCADE)
    
    # Generation context
    context_data = models.JSONField(default=dict, help_text="Additional context for content generation")
    target_category = models.ForeignKey('blog.Category', on_delete=models.CASCADE)
    
    # Processing
    processed = models.BooleanField(default=False)
    content_request = models.ForeignKey(
        'blog.ContentGenerationRequest',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    
    # Scheduling
    scheduled_for = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority', 'scheduled_for']
    
    panels = [
        MultiFieldPanel([
            FieldPanel('content_type'),
            FieldPanel('title'),
            FieldPanel('priority'),
            FieldPanel('target_category'),
        ], heading='Content Details'),
        
        MultiFieldPanel([
            FieldPanel('trending_topic'),
        ], heading='Data Sources'),
        
        MultiFieldPanel([
            FieldPanel('context_data'),
            FieldPanel('processed'),
            FieldPanel('content_request'),
        ], heading='Processing'),
        
        MultiFieldPanel([
            FieldPanel('scheduled_for'),
        ], heading='Scheduling'),
    ]

    def __str__(self):
        return f"{self.get_content_type_display()}: {self.title}"

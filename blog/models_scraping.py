"""
Models for web scraping and data-driven content generation.
"""
import json
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from wagtail.snippets.models import register_snippet


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
    """Raw scraped data from various sources."""

    source = models.ForeignKey(ScrapingSource, on_delete=models.CASCADE, related_name='scraped_items')

    # Item identification
    external_id = models.CharField(max_length=200, help_text="ID from the source website")
    url = models.URLField()
    title = models.CharField(max_length=500)

    # Content data
    description = models.TextField(blank=True)
    price = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=200, blank=True)
    tags = models.CharField(max_length=500, blank=True)

    # Images
    image_urls = models.JSONField(default=list, help_text="List of image URLs")

    # Metrics (for trending analysis)
    views = models.IntegerField(null=True, blank=True)
    likes = models.IntegerField(null=True, blank=True)
    sales = models.IntegerField(null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)

    # Additional metadata
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

    def __str__(self):
        return f"{self.title} ({self.source.website})"

    @property
    def is_trending(self):
        """Simple trending calculation based on recent metrics."""
        if not any([self.views, self.likes, self.sales]):
            return False

        # Basic trending logic - can be made more sophisticated
        score = (self.views or 0) + (self.likes or 0) * 2 + (self.sales or 0) * 5
        return score > 100


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
    
    def __str__(self):
        return f"{self.get_content_type_display()}: {self.title}"

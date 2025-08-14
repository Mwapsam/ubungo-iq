"""
Django admin for web scraping and data-driven content generation.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.utils.safestring import mark_safe
from .models_scraping import (
    ScrapingSource, ScrapedData, TrendingTopic, 
    ScrapingLog, ContentGenerationQueue
)


@admin.register(ScrapingSource)
class ScrapingSourceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'website', 'enabled', 'scrape_frequency_hours', 
        'last_scraped', 'last_success', 'consecutive_failures', 'health_status'
    ]
    list_filter = ['enabled', 'website', 'consecutive_failures']
    search_fields = ['name', 'base_url']
    readonly_fields = ['last_scraped', 'last_success', 'consecutive_failures', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'website', 'base_url', 'enabled')
        }),
        ('Scraping Configuration', {
            'fields': (
                'scrape_frequency_hours', 'max_items_per_scrape', 
                'request_delay_seconds', 'user_agent', 'scraping_config'
            )
        }),
        ('Status', {
            'fields': (
                'last_scraped', 'last_success', 'consecutive_failures'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def health_status(self, obj):
        """Display health status with colors."""
        if obj.consecutive_failures == 0:
            return format_html('<span style="color: green;">✓ Healthy</span>')
        elif obj.consecutive_failures < 3:
            return format_html('<span style="color: orange;">⚠ Warning</span>')
        else:
            return format_html('<span style="color: red;">✗ Unhealthy</span>')
    
    health_status.short_description = 'Health'
    
    actions = ['trigger_scraping', 'reset_failures']
    
    def trigger_scraping(self, request, queryset):
        """Trigger scraping for selected sources."""
        from .tasks_scraping import scrape_website
        
        count = 0
        for source in queryset.filter(enabled=True):
            scrape_website.delay(source.id)
            count += 1
        
        self.message_user(
            request,
            f'Triggered scraping for {count} sources.',
            messages.SUCCESS
        )
    
    trigger_scraping.short_description = "Trigger scraping for selected sources"
    
    def reset_failures(self, request, queryset):
        """Reset failure count for selected sources."""
        count = queryset.update(consecutive_failures=0)
        self.message_user(
            request,
            f'Reset failure count for {count} sources.',
            messages.SUCCESS
        )
    
    reset_failures.short_description = "Reset failure count"


@admin.register(ScrapedData)
class ScrapedDataAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'source', 'category', 'price', 'content_generated', 
        'scraped_at', 'data_actions'
    ]
    list_filter = [
        'source', 'content_generated', 'scraped_at', 'category'
    ]
    search_fields = ['title', 'description', 'category', 'tags']
    readonly_fields = ['scraped_at', 'updated_at', 'external_id']
    date_hierarchy = 'scraped_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('source', 'external_id', 'title', 'url')
        }),
        ('Content Data', {
            'fields': ('description', 'price', 'category', 'tags', 'image_urls')
        }),
        ('Metrics', {
            'fields': ('views', 'likes', 'sales', 'rating'),
            'classes': ('collapse',)
        }),
        ('Content Generation', {
            'fields': ('content_generated', 'content_generation_request'),
            'classes': ('collapse',)
        }),
        ('Raw Data', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('scraped_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def data_actions(self, obj):
        """Display action buttons."""
        buttons = []
        
        if not obj.content_generated:
            buttons.append(
                f'<a class="button" href="#" onclick="generateContent({obj.id})">🤖 Generate Content</a>'
            )
        
        if obj.url:
            buttons.append(
                f'<a class="button" href="{obj.url}" target="_blank">🔗 View Original</a>'
            )
        
        return format_html(' '.join(buttons))
    
    data_actions.short_description = 'Actions'
    data_actions.allow_tags = True
    
    actions = ['queue_for_content_generation']
    
    def queue_for_content_generation(self, request, queryset):
        """Queue selected items for content generation."""
        from blog.models import Category
        
        try:
            default_category = Category.objects.get(slug='tech')
        except Category.DoesNotExist:
            default_category = Category.objects.first()
        
        if not default_category:
            self.message_user(
                request,
                'No categories available. Create a category first.',
                messages.ERROR
            )
            return
        
        count = 0
        for item in queryset.filter(content_generated=False):
            ContentGenerationQueue.objects.get_or_create(
                target_category=default_category,
                defaults={
                    'content_type': 'product_review',
                    'title': f"Review: {item.title}",
                    'priority': 'normal',
                    'context_data': {
                        'scraped_item_id': item.id,
                        'source': item.source.name,
                        'price': item.price,
                        'category': item.category
                    }
                }
            )
            # Add the scraped item to the queue after creation
            queue_item = ContentGenerationQueue.objects.filter(
                title=f"Review: {item.title}"
            ).first()
            if queue_item:
                queue_item.scraped_items.add(item)
            
            count += 1
        
        self.message_user(
            request,
            f'Queued {count} items for content generation.',
            messages.SUCCESS
        )
    
    queue_for_content_generation.short_description = "Queue for content generation"


@admin.register(TrendingTopic)
class TrendingTopicAdmin(admin.ModelAdmin):
    list_display = [
        'topic', 'source', 'category', 'frequency', 'total_views', 
        'trending_score', 'content_generated', 'last_updated'
    ]
    list_filter = ['source', 'content_generated', 'category', 'last_updated']
    search_fields = ['topic', 'category']
    readonly_fields = ['trending_score', 'first_seen', 'last_updated']
    
    fieldsets = (
        ('Topic Information', {
            'fields': ('source', 'topic', 'category')
        }),
        ('Metrics', {
            'fields': ('frequency', 'total_views', 'total_sales', 'average_rating', 'trending_score')
        }),
        ('Sample Data', {
            'fields': ('sample_items',),
            'classes': ('collapse',)
        }),
        ('Content Generation', {
            'fields': ('content_generated', 'content_generation_request'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('first_seen', 'last_updated'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['generate_trend_content']
    
    def generate_trend_content(self, request, queryset):
        """Generate content for selected trending topics."""
        from .tasks_scraping import queue_trending_content
        
        for topic in queryset.filter(content_generated=False):
            queue_trending_content.delay(topic.source.id)
        
        self.message_user(
            request,
            f'Queued content generation for {queryset.count()} trending topics.',
            messages.SUCCESS
        )
    
    generate_trend_content.short_description = "Generate content for selected trends"


@admin.register(ScrapingLog)
class ScrapingLogAdmin(admin.ModelAdmin):
    list_display = [
        'source', 'status', 'items_found', 'items_new', 'items_updated', 
        'items_failed', 'duration_seconds', 'started_at'
    ]
    list_filter = ['status', 'source', 'started_at']
    readonly_fields = [
        'source', 'status', 'items_found', 'items_new', 'items_updated',
        'items_failed', 'started_at', 'completed_at', 'duration_seconds',
        'error_message', 'error_traceback', 'notes'
    ]
    date_hierarchy = 'started_at'
    
    def has_add_permission(self, request):
        return False  # Logs are created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Logs should not be edited


@admin.register(ContentGenerationQueue)
class ContentGenerationQueueAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'content_type', 'priority', 'target_category', 
        'processed', 'scheduled_for', 'created_at'
    ]
    list_filter = [
        'content_type', 'priority', 'target_category', 
        'processed', 'scheduled_for'
    ]
    search_fields = ['title']
    readonly_fields = ['created_at']
    filter_horizontal = ['scraped_items']
    
    fieldsets = (
        ('Content Details', {
            'fields': ('content_type', 'title', 'priority', 'target_category')
        }),
        ('Data Sources', {
            'fields': ('scraped_items', 'trending_topic')
        }),
        ('Context & Processing', {
            'fields': ('context_data', 'processed', 'content_request')
        }),
        ('Scheduling', {
            'fields': ('scheduled_for', 'created_at')
        }),
    )
    
    actions = ['process_selected_queue_items']
    
    def process_selected_queue_items(self, request, queryset):
        """Process selected queue items for content generation."""
        from .tasks_scraping import generate_content_from_data
        
        count = 0
        for item in queryset.filter(processed=False):
            generate_content_from_data.delay(item.id)
            count += 1
        
        self.message_user(
            request,
            f'Started processing {count} queue items.',
            messages.SUCCESS
        )
    
    process_selected_queue_items.short_description = "Process selected queue items"
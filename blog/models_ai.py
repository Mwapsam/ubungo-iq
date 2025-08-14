"""
Models for AI content generation tracking.
"""
from django.db import models
from django.contrib.auth.models import User
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.snippets.models import register_snippet
from blog.models import Category


@register_snippet
class ContentGenerationRequest(models.Model):
    """Track AI content generation requests."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('review', 'Ready for Review'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
    ]

    topic = models.CharField(max_length=200, help_text="Topic for content generation")
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # AI Generation metadata
    model_used = models.CharField(max_length=50, blank=True)
    prompt_used = models.TextField(blank=True)

    # Generated content
    generated_outline = models.TextField(blank=True)
    generated_content = models.TextField(blank=True)
    generated_title = models.CharField(max_length=200, blank=True)
    generated_meta_description = models.CharField(max_length=160, blank=True)
    generated_tags = models.TextField(blank=True, help_text="Comma-separated tags")

    # Workflow
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_requests')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='content_reviews')

    # Related article if published
    published_article = models.ForeignKey(
        'blog.ArticlePage', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    generation_started_at = models.DateTimeField(null=True, blank=True)
    generation_completed_at = models.DateTimeField(null=True, blank=True)

    # Quality metrics
    word_count = models.IntegerField(null=True, blank=True)
    generation_time_seconds = models.IntegerField(null=True, blank=True)

    # Review notes
    review_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Content Generation Request"
        verbose_name_plural = "Content Generation Requests"

    def __str__(self):
        return f"{self.topic} ({self.get_status_display()})"

    @property
    def is_ready_for_review(self):
        """Check if content is ready for human review."""
        return (
            self.status == 'review' and 
            self.generated_content and 
            self.generated_title
        )

    @property
    def can_be_published(self):
        """Check if content can be published."""
        return self.status == 'approved' and self.is_ready_for_review


@register_snippet
class AIContentMetrics(models.Model):
    """Track metrics for AI-generated content performance."""
    
    article = models.OneToOneField(
        'blog.ArticlePage',
        on_delete=models.CASCADE,
        related_name='ai_metrics'
    )
    generation_request = models.ForeignKey(
        ContentGenerationRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Generation metrics
    total_generation_time = models.IntegerField(help_text="Total time in seconds")
    outline_generation_time = models.IntegerField(null=True, blank=True)
    content_generation_time = models.IntegerField(null=True, blank=True)
    
    # Content quality metrics
    original_word_count = models.IntegerField()
    final_word_count = models.IntegerField()
    human_edit_percentage = models.FloatField(
        null=True, 
        blank=True,
        help_text="Percentage of content that was human-edited"
    )
    
    # Performance metrics (to be updated via analytics)
    avg_reading_time = models.FloatField(null=True, blank=True)
    bounce_rate = models.FloatField(null=True, blank=True)
    engagement_score = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "AI Content Metrics"
        verbose_name_plural = "AI Content Metrics"
    
    def __str__(self):
        return f"AI Metrics: {self.article.title}"

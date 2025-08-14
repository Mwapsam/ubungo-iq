"""
Django admin for AI content generation.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.shortcuts import redirect
from .models_ai import ContentGenerationRequest, AIContentMetrics
from utils.ai_client import ai_client


@admin.register(ContentGenerationRequest)
class ContentGenerationRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'topic', 'category', 'status', 'word_count', 
        'generation_time_seconds', 'created_at', 'action_buttons'
    ]
    list_filter = ['status', 'category', 'model_used', 'created_at']
    search_fields = ['topic', 'generated_title', 'generated_content']
    readonly_fields = [
        'created_at', 'updated_at', 'generation_started_at', 
        'generation_completed_at', 'model_used', 'prompt_used',
        'generation_time_seconds', 'word_count'
    ]
    
    fieldsets = (
        ('Request Details', {
            'fields': ('topic', 'category', 'status', 'requested_by', 'reviewed_by')
        }),
        ('Generated Content', {
            'fields': (
                'generated_title', 'generated_outline', 'generated_content',
                'generated_meta_description', 'generated_tags'
            ),
            'classes': ('collapse',)
        }),
        ('Generation Metadata', {
            'fields': (
                'model_used', 'prompt_used', 'word_count', 'generation_time_seconds'
            ),
            'classes': ('collapse',)
        }),
        ('Workflow', {
            'fields': ('review_notes', 'published_article'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'generation_started_at', 
                'generation_completed_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def action_buttons(self, obj):
        """Display action buttons for each request."""
        buttons = []
        
        if obj.status == 'pending':
            generate_url = reverse('admin:generate_content', args=[obj.id])
            buttons.append(
                f'<a class="button" href="{generate_url}">🤖 Generate</a>'
            )
        
        if obj.status == 'review' and obj.generated_content:
            preview_url = reverse('admin:preview_content', args=[obj.id])
            buttons.append(
                f'<a class="button" href="{preview_url}" target="_blank">👀 Preview</a>'
            )
            
            approve_url = reverse('admin:approve_content', args=[obj.id])
            buttons.append(
                f'<a class="button" href="{approve_url}">✅ Approve</a>'
            )
            
            reject_url = reverse('admin:reject_content', args=[obj.id])
            buttons.append(
                f'<a class="button" href="{reject_url}">❌ Reject</a>'
            )
        
        if obj.status == 'approved' and not obj.published_article:
            publish_url = reverse('admin:publish_content', args=[obj.id])
            buttons.append(
                f'<a class="button" href="{publish_url}">📝 Create Article</a>'
            )
        
        return format_html(' '.join(buttons))
    
    action_buttons.short_description = 'Actions'
    action_buttons.allow_tags = True
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'requested_by', 'reviewed_by', 'published_article'
        )
    
    actions = ['regenerate_content', 'bulk_approve', 'bulk_reject']
    
    def regenerate_content(self, request, queryset):
        """Regenerate content for selected requests."""
        count = 0
        for req in queryset.filter(status__in=['failed', 'rejected']):
            req.status = 'pending'
            req.generated_content = ''
            req.generated_outline = ''
            req.generated_title = ''
            req.review_notes = ''
            req.save()
            count += 1
        
        self.message_user(
            request, 
            f'Marked {count} requests for regeneration.',
            messages.SUCCESS
        )
    
    regenerate_content.short_description = "Mark selected items for regeneration"
    
    def bulk_approve(self, request, queryset):
        """Bulk approve content that's ready for review."""
        count = queryset.filter(status='review').update(
            status='approved',
            reviewed_by=request.user
        )
        
        self.message_user(
            request, 
            f'Approved {count} content requests.',
            messages.SUCCESS
        )
    
    bulk_approve.short_description = "Approve selected content"
    
    def bulk_reject(self, request, queryset):
        """Bulk reject content."""
        count = queryset.filter(status='review').update(
            status='rejected',
            reviewed_by=request.user,
            review_notes='Bulk rejected via admin'
        )
        
        self.message_user(
            request, 
            f'Rejected {count} content requests.',
            messages.SUCCESS
        )
    
    bulk_reject.short_description = "Reject selected content"


@admin.register(AIContentMetrics)
class AIContentMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'article', 'total_generation_time', 'original_word_count', 
        'final_word_count', 'human_edit_percentage', 'engagement_score'
    ]
    list_filter = ['created_at']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('article')


# Custom admin actions
def generate_content_action(modeladmin, request, obj_id):
    """Custom admin action to generate content."""
    # from django.contrib.admin.views.main import IS_POPUP_VAR, TO_FIELD_VAR
    from django.http import HttpResponseRedirect
    
    try:
        from django.utils import timezone
        from utils.ai_client import ai_client
        
        req = ContentGenerationRequest.objects.get(id=obj_id)
        if req.status != 'pending':
            messages.error(request, "Content can only be generated for pending requests.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))
        
        # Start generation process (this should ideally be async)
        req.status = 'generating'
        req.generation_started_at = timezone.now()
        req.model_used = ai_client.model
        req.save()
        
        # For now, we'll just mark it for manual generation
        # In production, you'd want to queue this with Celery
        messages.success(
            request, 
            f"Generation started for: {req.topic}. "
            f"Use the management command: python manage.py generate_content --topic \"{req.topic}\" --category {req.category.slug}"
        )
        
    except ContentGenerationRequest.DoesNotExist:
        messages.error(request, "Content generation request not found.")
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))


# Add this to the admin site URLs via a custom admin.py extension or URL pattern
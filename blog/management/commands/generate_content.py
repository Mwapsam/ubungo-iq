"""
Management command for AI content generation.
"""
import time
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from blog.models import Category
from blog.models_ai import ContentGenerationRequest
from utils.ai_client import ai_client


class Command(BaseCommand):
    help = 'Generate AI content for the blog'

    def add_arguments(self, parser):
        parser.add_argument(
            '--topic',
            type=str,
            help='Topic to generate content about'
        )
        
        parser.add_argument(
            '--category',
            type=str,
            help='Category slug for the content'
        )
        
        parser.add_argument(
            '--auto-approve',
            action='store_true',
            help='Automatically approve generated content'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without actually doing it'
        )
        
        parser.add_argument(
            '--list-models',
            action='store_true',
            help='List available AI models'
        )
        
        parser.add_argument(
            '--check-connection',
            action='store_true',
            help='Check Ollama connection'
        )
        
        parser.add_argument(
            '--bulk-generate',
            type=str,
            nargs='+',
            help='Generate content for multiple topics (space-separated)'
        )

    def handle(self, *args, **options):
        # Check connection command
        if options['check_connection']:
            self.check_ollama_connection()
            return
            
        # List models command  
        if options['list_models']:
            self.list_available_models()
            return
        
        # Bulk generation
        if options['bulk_generate']:
            self.bulk_generate_content(options)
            return
        
        # Single content generation
        if not options['topic']:
            raise CommandError('Please provide a --topic to generate content about')
            
        if not options['category']:
            raise CommandError('Please provide a --category for the content')
        
        self.generate_single_content(options)

    def check_ollama_connection(self):
        """Check if Ollama is accessible."""
        self.stdout.write("Checking Ollama connection...")
        
        if ai_client.check_connection():
            self.stdout.write(
                self.style.SUCCESS('✓ Ollama is running and accessible')
            )
            self.stdout.write(f"Base URL: {ai_client.base_url}")
            self.stdout.write(f"Model: {ai_client.model}")
        else:
            self.stdout.write(
                self.style.ERROR('✗ Cannot connect to Ollama. Make sure it\'s running.')
            )
            self.stdout.write("Start Ollama with: ollama serve")

    def list_available_models(self):
        """List available models in Ollama."""
        self.stdout.write("Available models:")
        
        models = ai_client.get_available_models()
        if models:
            for model in models:
                marker = "→" if model == ai_client.model else " "
                self.stdout.write(f"{marker} {model}")
        else:
            self.stdout.write(
                self.style.WARNING("No models found or Ollama not accessible")
            )

    def generate_single_content(self, options):
        """Generate content for a single topic."""
        topic = options['topic']
        category_slug = options['category']
        dry_run = options['dry_run']
        auto_approve = options['auto_approve']

        # Get category
        try:
            category = Category.objects.get(slug=category_slug)
        except Category.DoesNotExist:
            raise CommandError(f'Category "{category_slug}" does not exist')

        if dry_run:
            self.stdout.write(f"Would generate content for:")
            self.stdout.write(f"  Topic: {topic}")
            self.stdout.write(f"  Category: {category.name}")
            self.stdout.write(f"  Auto-approve: {auto_approve}")
            return

        # Get or create superuser for the request
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            raise CommandError("No superuser found. Create one with: python manage.py createsuperuser")

        # Create generation request
        request_obj = ContentGenerationRequest.objects.create(
            topic=topic,
            category=category,
            status='generating',
            model_used=ai_client.model,
            requested_by=user,
            generation_started_at=timezone.now()
        )

        self.stdout.write(f"Created generation request: {request_obj.id}")
        
        try:
            self.generate_content_for_request(request_obj, auto_approve)
        except Exception as e:
            request_obj.status = 'failed'
            request_obj.review_notes = f"Error: {str(e)}"
            request_obj.save()
            raise CommandError(f"Content generation failed: {e}")

    def generate_content_for_request(self, request_obj, auto_approve=False):
        """Generate content for a specific request."""
        start_time = time.time()
        
        self.stdout.write(f"Generating content for: {request_obj.topic}")
        
        # Step 1: Generate outline
        self.stdout.write("1. Generating outline...")
        outline = ai_client.generate_article_outline(
            request_obj.topic, 
            request_obj.category.name
        )
        
        if not outline:
            raise Exception("Failed to generate outline")
            
        request_obj.generated_outline = outline
        request_obj.save()
        
        self.stdout.write("   ✓ Outline generated")
        
        # Step 2: Generate content
        self.stdout.write("2. Generating article content...")
        content = ai_client.generate_article_content(outline)
        
        if not content:
            raise Exception("Failed to generate content")
            
        request_obj.generated_content = content
        request_obj.word_count = len(content.split())
        request_obj.save()
        
        self.stdout.write(f"   ✓ Content generated ({request_obj.word_count} words)")
        
        # Step 3: Generate SEO elements
        self.stdout.write("3. Generating SEO elements...")
        
        title = ai_client.generate_seo_title(content)
        if title:
            request_obj.generated_title = title.strip().strip('"')
            
        meta_desc = ai_client.generate_meta_description(content)
        if meta_desc:
            request_obj.generated_meta_description = meta_desc.strip().strip('"')
        
        # Mark completion
        end_time = time.time()
        request_obj.generation_time_seconds = int(end_time - start_time)
        request_obj.generation_completed_at = timezone.now()
        
        if auto_approve:
            request_obj.status = 'approved'
            self.stdout.write("   ✓ Content auto-approved")
        else:
            request_obj.status = 'review'
            self.stdout.write("   ✓ Content ready for review")
            
        request_obj.save()
        
        # Show summary
        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 Content generation completed!")
        )
        self.stdout.write(f"Request ID: {request_obj.id}")
        self.stdout.write(f"Title: {request_obj.generated_title}")
        self.stdout.write(f"Word count: {request_obj.word_count}")
        self.stdout.write(f"Generation time: {request_obj.generation_time_seconds}s")
        self.stdout.write(f"Status: {request_obj.get_status_display()}")
        
        if not auto_approve:
            self.stdout.write(f"\nReview at: /admin/blog/contentgenerationrequest/{request_obj.id}/")

    def bulk_generate_content(self, options):
        """Generate content for multiple topics."""
        topics = options['bulk_generate']
        category_slug = options.get('category')
        auto_approve = options.get('auto_approve', False)
        
        if not category_slug:
            raise CommandError('--category is required for bulk generation')
            
        try:
            category = Category.objects.get(slug=category_slug)
        except Category.DoesNotExist:
            raise CommandError(f'Category "{category_slug}" does not exist')

        self.stdout.write(f"Bulk generating {len(topics)} articles for category: {category.name}")
        
        for i, topic in enumerate(topics, 1):
            self.stdout.write(f"\n--- Generating {i}/{len(topics)}: {topic} ---")
            
            # Create individual options for single generation
            single_options = {
                'topic': topic,
                'category': category_slug,
                'auto_approve': auto_approve,
                'dry_run': False
            }
            
            try:
                self.generate_single_content(single_options)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to generate content for '{topic}': {e}")
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Bulk generation completed! Generated content for {len(topics)} topics.")
        )
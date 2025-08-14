"""
Simple AI test command for debugging.
"""
from django.core.management.base import BaseCommand
from utils.ai_client import ai_client


class Command(BaseCommand):
    help = 'Test AI generation with simple prompts'

    def handle(self, *args, **options):
        self.stdout.write("Testing AI generation...")
        
        # Simple test
        prompt = "Write a title for an article about Django web development:"
        
        self.stdout.write(f"Prompt: {prompt}")
        self.stdout.write("Generating...")
        
        try:
            result = ai_client.generate_text(prompt, max_tokens=50, temperature=0.5)
            
            if result:
                self.stdout.write(self.style.SUCCESS(f"✓ Generated: {result}"))
            else:
                self.stdout.write(self.style.ERROR("✗ No result"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error: {e}"))
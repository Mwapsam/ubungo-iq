"""
AI Client for content generation using Ollama.
"""
import json
import logging
import requests
from typing import Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API for content generation."""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.enabled = settings.CONTENT_GENERATION_ENABLED
    
    def generate_text(
        self, 
        prompt: str, 
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Optional[str]:
        """
        Generate text using Ollama.
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Creativity level (0.0-1.0)
            stream: Whether to stream the response
            
        Returns:
            Generated text or None if error
        """
        if not self.enabled:
            logger.warning("AI content generation is disabled")
            return None
            
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": stream,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                },
                timeout=120  # 2 minute timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "").strip()
                if not generated_text:
                    logger.error(f"Ollama returned empty response for prompt: {prompt[:100]}...")
                return generated_text
            else:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                print(f"DEBUG: {error_msg}")  # Also print to stdout for debugging
                return None
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error connecting to Ollama: {e}"
            logger.error(error_msg)
            print(f"DEBUG: {error_msg}")  # Also print to stdout for debugging
            return None
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing Ollama response: {e}"
            logger.error(error_msg)
            print(f"DEBUG: {error_msg}")  # Also print to stdout for debugging
            return None
    
    def generate_article_outline(self, topic: str, category: str) -> Optional[str]:
        """Generate an article outline for the given topic and category."""
        prompt = settings.AI_PROMPTS["article_outline"].format(
            topic=topic, 
            category=category
        )
        
        logger.info(f"Generating outline for topic: {topic}")
        return self.generate_text(prompt, max_tokens=1000, temperature=0.7)
    
    def generate_article_content(self, outline: str) -> Optional[str]:
        """Generate full article content based on an outline."""
        prompt = settings.AI_PROMPTS["article_content"].format(outline=outline)
        
        logger.info("Generating article content from outline")
        return self.generate_text(prompt, max_tokens=3000, temperature=0.6)
    
    def generate_seo_title(self, content: str) -> Optional[str]:
        """Generate an SEO-optimized title for the content."""
        prompt = f"""Based on this article content, create an SEO-optimized title that is:
- Engaging and clickable
- Under 60 characters
- Includes relevant keywords
- Suitable for a technology blog

Article content excerpt:
{content[:500]}...

Generate only the title, nothing else."""
        
        return self.generate_text(prompt, max_tokens=100, temperature=0.5)
    
    def generate_meta_description(self, content: str) -> Optional[str]:
        """Generate a meta description for SEO."""
        prompt = f"""Create a compelling meta description (150-160 characters) for this article:

{content[:800]}...

The meta description should:
- Summarize the key points
- Include a call to action
- Be under 160 characters
- Be engaging for search results

Generate only the meta description, nothing else."""
        
        return self.generate_text(prompt, max_tokens=50, temperature=0.5)
    
    def check_connection(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_available_models(self) -> list:
        """Get list of available models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except requests.exceptions.RequestException:
            return []


# Global instance
ai_client = OllamaClient()
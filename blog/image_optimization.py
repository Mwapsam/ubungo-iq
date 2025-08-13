# blog/image_optimization.py
from django.conf import settings
from wagtail.images.models import AbstractImage, AbstractRendition
from wagtail.images.rect import Rect
from PIL import Image, ImageOps
import pillow_avif
import os
import logging

logger = logging.getLogger(__name__)


class OptimizedImageMixin:
    """Mixin for optimized image handling."""
    
    def get_webp_rendition(self, filter_spec):
        """Get WebP rendition with fallback."""
        try:
            webp_filter = f"{filter_spec}|format-webp"
            return self.get_rendition(webp_filter)
        except Exception as e:
            logger.warning(f"WebP rendition failed: {e}")
            return self.get_rendition(filter_spec)
    
    def get_avif_rendition(self, filter_spec):
        """Get AVIF rendition with fallback."""
        try:
            avif_filter = f"{filter_spec}|format-avif"
            return self.get_rendition(avif_filter)
        except Exception as e:
            logger.warning(f"AVIF rendition failed: {e}")
            return self.get_webp_rendition(filter_spec)
    
    def get_responsive_images(self, base_filter="fill-800x600"):
        """Get responsive image set with multiple formats and sizes."""
        sizes = {
            'small': base_filter.replace('800x600', '400x300'),
            'medium': base_filter.replace('800x600', '600x450'), 
            'large': base_filter,
            'xlarge': base_filter.replace('800x600', '1200x900'),
        }
        
        responsive_set = {}
        for size_name, filter_spec in sizes.items():
            responsive_set[size_name] = {
                'avif': self.get_avif_rendition(filter_spec),
                'webp': self.get_webp_rendition(filter_spec),
                'original': self.get_rendition(filter_spec)
            }
            
        return responsive_set
    
    def get_optimized_url(self, filter_spec, format_preference=None):
        """Get optimized image URL based on format preference."""
        if format_preference == 'avif':
            return self.get_avif_rendition(filter_spec).url
        elif format_preference == 'webp':
            return self.get_webp_rendition(filter_spec).url
        else:
            return self.get_rendition(filter_spec).url


def optimize_image_on_upload(image_file, quality=85):
    """Optimize image on upload."""
    try:
        with Image.open(image_file) as img:
            # Auto-rotate based on EXIF data
            img = ImageOps.exif_transpose(img)
            
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1])
                img = background
            
            # Compress based on size
            if img.size[0] > 2000 or img.size[1] > 2000:
                img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                quality = 80
            elif img.size[0] > 1200 or img.size[1] > 1200:
                quality = 85
            
            # Save optimized version
            img.save(
                image_file,
                format='JPEG',
                quality=quality,
                optimize=True,
                progressive=True
            )
            
    except Exception as e:
        logger.error(f"Image optimization failed: {e}")
        
    return image_file


class ImageCompressionSettings:
    """Centralized image compression settings."""
    
    FORMATS = {
        'JPEG': {
            'quality': 85,
            'optimize': True,
            'progressive': True
        },
        'WebP': {
            'quality': 80,
            'method': 4,  # 0-6, higher = better compression
            'lossless': False
        },
        'AVIF': {
            'quality': 70,
            'speed': 4,  # 0-10, higher = faster encoding
        }
    }
    
    # Responsive breakpoints
    RESPONSIVE_SIZES = [
        (320, 'mobile'),
        (640, 'tablet'),
        (1024, 'desktop'),
        (1440, 'desktop-large'),
        (1920, 'desktop-xl')
    ]
    
    # Maximum dimensions
    MAX_ORIGINAL_SIZE = (3000, 3000)
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
    
    @classmethod
    def get_quality_for_size(cls, width, height):
        """Get appropriate quality based on image size."""
        total_pixels = width * height
        
        if total_pixels > 2_000_000:  # > 2MP
            return 70
        elif total_pixels > 1_000_000:  # > 1MP
            return 80
        else:
            return 85
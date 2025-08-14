"""
Management command to set up initial scraping sources.
"""
from django.core.management.base import BaseCommand
from blog.models_scraping import ScrapingSource


class Command(BaseCommand):
    help = 'Set up initial scraping sources with default configurations'

    def handle(self, *args, **options):
        self.stdout.write("Setting up scraping sources...")
        
        # Alibaba B2B configuration
        alibaba, created = ScrapingSource.objects.get_or_create(
            website='alibaba',
            defaults={
                'name': 'Alibaba B2B Marketplace',
                'base_url': 'https://www.alibaba.com',
                'scrape_frequency_hours': 24,
                'max_items_per_scrape': 50,
                'request_delay_seconds': 3.0,
                'scraping_config': {
                    'search_terms': [
                        'electronics', 'clothing', 'machinery', 'home-garden',
                        'automotive', 'beauty-personal-care', 'sports'
                    ],
                    'selectors': {
                        'product_cards': '.organic-list-item',
                        'title': '.elements-title-normal a',
                        'price': '.price-current',
                        'supplier': '.supplier a'
                    }
                }
            }
        )
        if created:
            self.stdout.write(f"✓ Created Alibaba scraping source")
        else:
            self.stdout.write(f"- Alibaba scraping source already exists")
        
        # GlobalTrade.net configuration
        globaltrade, created = ScrapingSource.objects.get_or_create(
            website='globaltrade',
            defaults={
                'name': 'GlobalTrade.net',
                'base_url': 'https://www.globaltrade.net',
                'scrape_frequency_hours': 48,  # Less frequent, more stable data
                'max_items_per_scrape': 30,
                'request_delay_seconds': 4.0,
                'scraping_config': {
                    'categories': ['exporters', 'importers', 'manufacturers', 'suppliers'],
                    'selectors': {
                        'listings': '.company, .listing, .item',
                        'company_name': 'a',
                        'description': 'p, .description',
                        'location': '.location, .country'
                    }
                }
            }
        )
        if created:
            self.stdout.write(f"✓ Created GlobalTrade scraping source")
        else:
            self.stdout.write(f"- GlobalTrade scraping source already exists")
        
        # Etsy configuration
        etsy, created = ScrapingSource.objects.get_or_create(
            website='etsy',
            defaults={
                'name': 'Etsy Marketplace',
                'base_url': 'https://www.etsy.com',
                'scrape_frequency_hours': 12,  # More frequent for trending products
                'max_items_per_scrape': 40,
                'request_delay_seconds': 2.5,
                'scraping_config': {
                    'trending_searches': [
                        'handmade jewelry', 'custom gifts', 'vintage decor',
                        'digital prints', 'craft supplies', 'wedding decor'
                    ],
                    'selectors': {
                        'product_cards': '[data-test-id="listing-card"]',
                        'title': '[data-test-id="listing-link"]',
                        'price': '.price',
                        'shop': '.shop-name',
                        'rating': '.rating'
                    }
                }
            }
        )
        if created:
            self.stdout.write(f"✓ Created Etsy scraping source")
        else:
            self.stdout.write(f"- Etsy scraping source already exists")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Scraping setup complete! "
                f"Configured {ScrapingSource.objects.filter(enabled=True).count()} sources."
            )
        )
        
        self.stdout.write("\nNext steps:")
        self.stdout.write("1. Run: python manage.py run_scrapers --test")
        self.stdout.write("2. Check admin: /admin/blog/scrapingsource/")
        self.stdout.write("3. Start periodic scraping with Celery Beat")

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing scraping sources to defaults'
        )
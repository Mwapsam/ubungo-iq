"""
Management command to run web scrapers.
"""
from django.core.management.base import BaseCommand, CommandError
from blog.models_scraping import ScrapingSource
from blog.tasks_scraping import scrape_website, periodic_scraping_scheduler


class Command(BaseCommand):
    help = 'Run web scrapers for data collection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Specific source to scrape (alibaba, globaltrade, etsy)'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Scrape all enabled sources'
        )
        
        parser.add_argument(
            '--test',
            action='store_true',
            help='Run a test scrape (smaller dataset)'
        )
        
        parser.add_argument(
            '--schedule',
            action='store_true',
            help='Run the periodic scheduler to check all due sources'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be scraped without actually doing it'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug mode with detailed logging'
        )
        
        parser.add_argument(
            '--list-sources',
            action='store_true',
            help='List all available scraping sources'
        )

    def handle(self, *args, **options):
        # Set debug mode if requested
        self.debug_mode = options.get('debug', False)
        
        if options['list_sources']:
            self.list_available_sources()
            return
            
        if options['schedule']:
            self.run_scheduler()
            return
            
        if options['dry_run']:
            self.show_scraping_plan(options)
            return
            
        if options['source']:
            self.scrape_single_source(options['source'], options['test'])
        elif options['all']:
            self.scrape_all_sources(options['test'])
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Please specify --source, --all, or --schedule"
                )
            )
            self.stdout.write("Examples:")
            self.stdout.write("  python manage.py run_scrapers --source alibaba")
            self.stdout.write("  python manage.py run_scrapers --all")
            self.stdout.write("  python manage.py run_scrapers --schedule")

    def run_scheduler(self):
        """Run the periodic scheduler."""
        self.stdout.write("Running periodic scraping scheduler...")
        
        try:
            result = periodic_scraping_scheduler.delay()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Scheduler task queued: {result.id}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Failed to queue scheduler: {e}")
            )

    def scrape_single_source(self, source_name, test_mode=False):
        """Scrape a single source."""
        try:
            source = ScrapingSource.objects.get(website=source_name, enabled=True)
        except ScrapingSource.DoesNotExist:
            # Show available sources for debugging
            available_sources = list(ScrapingSource.objects.values_list('website', flat=True))
            if available_sources:
                raise CommandError(f'Source "{source_name}" not found or disabled. Available: {", ".join(available_sources)}')
            else:
                raise CommandError(f'Source "{source_name}" not found. No sources configured - run: python manage.py setup_scrapers')
        
        self.stdout.write(f"Starting scrape of {source.name}...")
        
        if self.debug_mode:
            self.stdout.write(f"Source details:")
            self.stdout.write(f"  ID: {source.id}")
            self.stdout.write(f"  Base URL: {source.base_url}")
            self.stdout.write(f"  Last scraped: {source.last_scraped}")
            self.stdout.write(f"  Consecutive failures: {source.consecutive_failures}")
            self.stdout.write(f"  User agent: {source.user_agent or 'Default'}")
        
        if test_mode:
            self.stdout.write("Running in test mode (limited items)")
            # Update config for test mode
            original_max = source.max_items_per_scrape
            source.max_items_per_scrape = min(10, original_max)
            
            if self.debug_mode:
                self.stdout.write(f"  Original max items: {original_max}")
                self.stdout.write(f"  Test mode max items: {source.max_items_per_scrape}")
        
        try:
            if self.debug_mode:
                # Test basic connectivity first
                import requests
                self.stdout.write(f"Testing connectivity to {source.base_url}...")
                try:
                    response = requests.head(source.base_url, timeout=10)
                    self.stdout.write(f"  ✓ HTTP {response.status_code}")
                except requests.RequestException as e:
                    self.stdout.write(f"  ✗ Connection failed: {e}")
            
            result = scrape_website.delay(source.id)
            self.stdout.write(
                self.style.SUCCESS(f"✓ Scraping task queued: {result.id}")
            )
            self.stdout.write("Check the admin interface to monitor progress")
            self.stdout.write(f"Admin URL: /admin/blog/scrapingsource/{source.id}/")
            
            if self.debug_mode:
                self.stdout.write(f"Celery task ID: {result.id}")
                self.stdout.write("Monitor logs with: celery -A ubongo events")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Failed to queue scraping task: {e}")
            )
            
            if self.debug_mode:
                import traceback
                self.stdout.write("Full traceback:")
                self.stdout.write(traceback.format_exc())
        
        if test_mode:
            # Restore original config
            source.max_items_per_scrape = original_max

    def scrape_all_sources(self, test_mode=False):
        """Scrape all enabled sources."""
        sources = ScrapingSource.objects.filter(enabled=True)
        
        if not sources.exists():
            self.stdout.write(
                self.style.WARNING("No enabled scraping sources found")
            )
            self.stdout.write("Run: python manage.py setup_scrapers")
            return
        
        self.stdout.write(f"Starting scrape of {sources.count()} sources...")
        
        queued_count = 0
        for source in sources:
            try:
                if test_mode:
                    original_max = source.max_items_per_scrape
                    source.max_items_per_scrape = min(5, original_max)
                
                result = scrape_website.delay(source.id)
                self.stdout.write(f"✓ Queued {source.name}: {result.id}")
                queued_count += 1
                
                if test_mode:
                    source.max_items_per_scrape = original_max
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to queue {source.name}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 Queued {queued_count} scraping tasks")
        )

    def list_available_sources(self):
        """List all available scraping sources with details."""
        sources = ScrapingSource.objects.all()
        
        if not sources.exists():
            self.stdout.write(
                self.style.WARNING("No scraping sources found")
            )
            self.stdout.write("Run: python manage.py setup_scrapers")
            return
        
        self.stdout.write("Available scraping sources:")
        self.stdout.write("-" * 60)
        
        for source in sources:
            status_icon = "✓" if source.enabled else "✗"
            due_status = "DUE" if source.is_due_for_scraping else "NOT DUE"
            health_icon = "🔴" if source.consecutive_failures > 3 else "🟡" if source.consecutive_failures > 0 else "🟢"
            
            self.stdout.write(f"{status_icon} {source.name} ({source.website})")
            enabled_status = "Enabled" if source.enabled else "Disabled"
            self.stdout.write(f"   Status: {enabled_status} | {due_status}")
            self.stdout.write(f"   Last scraped: {source.last_scraped or 'Never'}")
            self.stdout.write(f"   Frequency: Every {source.scrape_frequency_hours} hours")
            self.stdout.write(f"   Max items per scrape: {source.max_items_per_scrape}")
            self.stdout.write(f"   Health: {health_icon} {source.consecutive_failures} consecutive failures")
            
            if self.debug_mode:
                self.stdout.write(f"   Base URL: {source.base_url}")
                self.stdout.write(f"   User agent: {source.user_agent or 'Default'}")
                self.stdout.write(f"   Request delay: {source.request_delay_seconds}s")
                self.stdout.write(f"   Scraping config: {source.scraping_config or 'Not configured'}")
            
            self.stdout.write("")
        
        # Summary statistics
        total_count = sources.count()
        enabled_count = sources.filter(enabled=True).count()
        due_count = len([s for s in sources if s.is_due_for_scraping])
        failed_count = sources.filter(consecutive_failures__gt=0).count()
        
        self.stdout.write(f"Summary: {total_count} total, {enabled_count} enabled, {due_count} due, {failed_count} with failures")

    def show_scraping_plan(self, options):
        """Show what would be scraped without doing it."""
        if options['source']:
            try:
                source = ScrapingSource.objects.get(website=options['source'])
                sources = [source]
            except ScrapingSource.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Source "{options["source"]}" not found')
                )
                return
        else:
            sources = ScrapingSource.objects.filter(enabled=True)
        
        self.stdout.write("Scraping Plan:")
        self.stdout.write("-" * 50)
        
        for source in sources:
            status = "✓" if source.enabled else "✗"
            due_status = "DUE" if source.is_due_for_scraping else "NOT DUE"
            
            self.stdout.write(f"{status} {source.name}")
            self.stdout.write(f"  Website: {source.website}")
            self.stdout.write(f"  Status: {due_status}")
            self.stdout.write(f"  Last scraped: {source.last_scraped or 'Never'}")
            self.stdout.write(f"  Frequency: Every {source.scrape_frequency_hours} hours")
            self.stdout.write(f"  Max items: {source.max_items_per_scrape}")
            self.stdout.write(f"  Health: {source.consecutive_failures} failures")
            
            if self.debug_mode:
                self.stdout.write(f"  Base URL: {source.base_url}")
                self.stdout.write(f"  User Agent: {source.user_agent or 'Default'}")
                self.stdout.write(f"  Request delay: {source.request_delay_seconds}s")
            
            self.stdout.write("")
        
        enabled_count = sources.filter(enabled=True).count()
        due_count = len([s for s in sources if s.is_due_for_scraping])
        
        self.stdout.write(f"Summary: {enabled_count} enabled, {due_count} due for scraping")
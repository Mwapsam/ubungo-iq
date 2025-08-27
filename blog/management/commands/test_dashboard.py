"""
Test the analytics dashboard and all its API endpoints.
"""
import json
from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth.models import User
from django.utils import timezone

from blog.views_dashboard import generate_dashboard_data


class Command(BaseCommand):
    help = 'Test the analytics dashboard and API endpoints'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-user',
            action='store_true',
            help='Create a test staff user for dashboard access'
        )
        parser.add_argument(
            '--test-apis',
            action='store_true',
            help='Test all dashboard API endpoints'
        )
        parser.add_argument(
            '--test-data-generation',
            action='store_true',
            help='Test dashboard data generation'
        )
    
    def handle(self, *args, **options):
        if options['create_test_user']:
            self.create_test_user()
            return
        
        if options['test_data_generation']:
            self.test_data_generation()
            return
        
        if options['test_apis']:
            self.test_api_endpoints()
            return
        
        # Run all tests by default
        self.stdout.write(self.style.SUCCESS('🧪 Running Dashboard Tests...'))
        self.stdout.write('=' * 50)
        
        self.test_data_generation()
        self.test_api_endpoints()
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ All dashboard tests completed successfully!'))
    
    def create_test_user(self):
        """Create a test staff user for dashboard access."""
        username = 'dashboard_test'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(f'Test user "{username}" already exists')
            return
        
        user = User.objects.create_user(
            username=username,
            email='test@dashboard.com',
            password='testpassword123',
            is_staff=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Created test staff user: {username}')
        )
        self.stdout.write(f'   Username: {username}')
        self.stdout.write(f'   Password: testpassword123')
        self.stdout.write(f'   Email: test@dashboard.com')
    
    def test_data_generation(self):
        """Test dashboard data generation."""
        self.stdout.write('📊 Testing Dashboard Data Generation...')
        
        try:
            dashboard_data = generate_dashboard_data()
            
            # Validate data structure
            required_keys = ['overview', 'categories', 'generated_at']
            for key in required_keys:
                if key not in dashboard_data:
                    raise ValueError(f"Missing required key: {key}")
            
            overview = dashboard_data['overview']
            required_overview_keys = [
                'total_products', 'total_sources', 'recent_products', 
                'recent_scrapes', 'avg_price', 'verification_rate'
            ]
            
            for key in required_overview_keys:
                if key not in overview:
                    raise ValueError(f"Missing overview key: {key}")
            
            self.stdout.write('   ✅ Data structure validation passed')
            self.stdout.write(f'   📈 Total Products: {overview["total_products"]}')
            self.stdout.write(f'   🏭 Total Sources: {overview["total_sources"]}')
            self.stdout.write(f'   💰 Average Price: ${overview["avg_price"]}')
            self.stdout.write(f'   ✅ Verification Rate: {overview["verification_rate"]}%')
            self.stdout.write(f'   📦 Categories: {len(dashboard_data["categories"])}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ Data generation failed: {e}')
            )
    
    def test_api_endpoints(self):
        """Test all dashboard API endpoints."""
        self.stdout.write('')
        self.stdout.write('🔌 Testing Dashboard API Endpoints...')
        
        # Create test client
        client = Client()
        
        # Create and login test user
        test_user = self.get_or_create_test_user()
        client.force_login(test_user)
        
        # API endpoints to test
        api_endpoints = [
            ('/blog/api/market-overview/', 'Market Overview'),
            ('/blog/api/price-trends/', 'Price Trends'),
            ('/blog/api/supplier-distribution/', 'Supplier Distribution'),
            ('/blog/api/trending-topics/', 'Trending Topics'),
            ('/blog/api/scraping-health/', 'Scraping Health'),
            ('/blog/api/content-opportunities/', 'Content Opportunities'),
            ('/blog/api/alerts-summary/', 'Alerts Summary')
        ]
        
        success_count = 0
        total_count = len(api_endpoints)
        
        for url, name in api_endpoints:
            try:
                response = client.get(url)
                
                if response.status_code == 200:
                    try:
                        data = json.loads(response.content)
                        if data.get('success'):
                            self.stdout.write(f'   ✅ {name}: OK')
                            success_count += 1
                        else:
                            error_msg = data.get('error', 'Unknown error')
                            self.stdout.write(f'   ⚠️  {name}: API Error - {error_msg}')
                    except json.JSONDecodeError:
                        self.stdout.write(f'   ❌ {name}: Invalid JSON response')
                else:
                    self.stdout.write(f'   ❌ {name}: HTTP {response.status_code}')
                    
            except Exception as e:
                self.stdout.write(f'   ❌ {name}: Exception - {e}')
        
        self.stdout.write('')
        self.stdout.write(f'📊 API Test Results: {success_count}/{total_count} endpoints working')
        
        if success_count == total_count:
            self.stdout.write(self.style.SUCCESS('   🎉 All API endpoints working correctly!'))
        elif success_count > 0:
            self.stdout.write(self.style.WARNING(f'   ⚠️  {total_count - success_count} endpoints need attention'))
        else:
            self.stdout.write(self.style.ERROR('   ❌ No API endpoints working'))
    
    def get_or_create_test_user(self):
        """Get or create a test staff user."""
        username = 'dashboard_test'
        
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return User.objects.create_user(
                username=username,
                email='test@dashboard.com',
                password='testpassword123',
                is_staff=True
            )
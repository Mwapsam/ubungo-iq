from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Check current database and cache configuration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🔍 Current Configuration:"))
        self.stdout.write("")
        
        # Environment
        use_postgres = os.environ.get('USE_POSTGRES', 'false').lower() == 'true'
        self.stdout.write(f"USE_POSTGRES: {use_postgres}")
        self.stdout.write("")
        
        # Database
        db_config = settings.DATABASES['default']
        self.stdout.write(self.style.SUCCESS("📊 Database:"))
        self.stdout.write(f"  Engine: {db_config['ENGINE']}")
        
        if 'postgresql' in db_config['ENGINE']:
            self.stdout.write(f"  Name: {db_config['NAME']}")
            self.stdout.write(f"  User: {db_config['USER']}")
            self.stdout.write(f"  Host: {db_config['HOST']}")
            self.stdout.write(f"  Port: {db_config['PORT']}")
        else:
            self.stdout.write(f"  File: {db_config['NAME']}")
        
        self.stdout.write("")
        
        # Cache
        cache_config = settings.CACHES['default']
        self.stdout.write(self.style.SUCCESS("🗄️  Cache:"))
        self.stdout.write(f"  Backend: {cache_config['BACKEND']}")
        if 'redis' in cache_config['BACKEND'].lower():
            self.stdout.write(f"  Location: {cache_config.get('LOCATION', 'Not specified')}")
        
        self.stdout.write("")
        
        # Celery
        self.stdout.write(self.style.SUCCESS("🔄 Celery:"))
        self.stdout.write(f"  Broker: {settings.CELERY_BROKER_URL}")
        self.stdout.write(f"  Result Backend: {settings.CELERY_RESULT_BACKEND}")
        
        self.stdout.write("")
        
        # Usage instructions
        self.stdout.write(self.style.WARNING("💡 To switch databases:"))
        if use_postgres:
            self.stdout.write("  To SQLite: Remove/rename .env.local or set USE_POSTGRES=false")
        else:
            self.stdout.write("  To PostgreSQL: Set USE_POSTGRES=true in environment or .env.local")
            self.stdout.write("  Quick setup: ./setup_postgres_local.sh")
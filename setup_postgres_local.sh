#!/bin/bash

# Setup script for local PostgreSQL development
# This script helps set up PostgreSQL for local development

echo "🐘 Setting up PostgreSQL for local development..."

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed. Please install it first:"
    echo "   macOS: brew install postgresql"
    echo "   Ubuntu: sudo apt-get install postgresql postgresql-contrib"
    echo "   Windows: Download from https://www.postgresql.org/download/"
    exit 1
fi

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "❌ Redis is not installed. Please install it first:"
    echo "   macOS: brew install redis"
    echo "   Ubuntu: sudo apt-get install redis-server"
    echo "   Windows: Download from https://redis.io/download"
    exit 1
fi

# Database configuration
DB_NAME="ubongo_iq_dev"
DB_USER="ubongo_iq_user"
DB_PASSWORD="ubongo_dev_password"

echo "📊 Creating PostgreSQL database and user..."

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;" 2>/dev/null || true

# For macOS with Homebrew PostgreSQL
if [[ "$OSTYPE" == "darwin"* ]]; then
    createdb $DB_NAME 2>/dev/null || true
    psql postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
    psql postgres -c "ALTER USER $DB_USER CREATEDB;" 2>/dev/null || true
fi

echo "📝 Creating local environment file..."

# Create .env.local with PostgreSQL configuration
cat > .env.local << EOF
# Local PostgreSQL configuration
USE_POSTGRES=true

# Database configuration
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=$DB_NAME
DATABASE_USER=$DB_USER
DATABASE_PASSWORD=$DB_PASSWORD
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Redis configuration
REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# AI Content Generation
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=tinyllama:latest
CONTENT_GENERATION_ENABLED=true
EOF

echo "🔧 Installing Python dependencies..."
poetry install

echo "🗄️  Running database migrations..."
export $(cat .env.local | grep -v '^#' | xargs)
poetry run python manage.py migrate

echo "👤 Creating superuser (optional)..."
echo "Do you want to create a superuser? (y/n)"
read -r create_superuser
if [[ $create_superuser == "y" ]]; then
    poetry run python manage.py createsuperuser
fi

echo "✅ PostgreSQL setup complete!"
echo ""
echo "🚀 To use PostgreSQL for development:"
echo "   1. Start Redis: redis-server"
echo "   2. Start Celery: poetry run celery -A ubongo worker --loglevel=info"
echo "   3. Start Django: poetry run python manage.py runserver"
echo ""
echo "💡 To switch back to SQLite, remove or rename .env.local"
echo ""
echo "🔗 Database connection: postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
#!/bin/bash

# Taruvi Traefik Setup Script
# This script sets up Traefik for local multi-tenant development

set -e

echo "🚀 Setting up Traefik for Taruvi multi-tenant development"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose >/dev/null 2>&1; then
    echo "❌ docker-compose is not installed. Please install it and try again."
    exit 1
fi

echo "✅ Docker and docker-compose are available"

# Ask user about database setup
echo ""
echo "🗄️  Database Setup Options:"
echo "1. Use containerized PostgreSQL (recommended for new setups)"
echo "2. Use external database (I have my own PostgreSQL running)"
echo ""
read -p "Choose option (1 or 2): " db_choice

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.yml down 2>/dev/null || true

if [ "$db_choice" = "1" ]; then
    echo "🏗️ Building and starting services with containerized database..."
    docker-compose -f docker-compose.yml --profile db up -d --build
    
    # Wait for database to be ready
    echo "⏳ Waiting for database to be ready..."
    sleep 15
    
elif [ "$db_choice" = "2" ]; then
    echo "🏗️ Building and starting services (using external database)..."
    echo "⚠️  Make sure your external database is running and accessible"
    echo "📝 Update your .env file with correct database credentials:"
    echo "   DB_HOST=localhost (or your database host)"
    echo "   DB_NAME=your_database_name"
    echo "   DB_USER=your_username"
    echo "   DB_PASSWORD=your_password"
    echo ""
    read -p "Press Enter when your database is ready and .env is configured..."
    
    # Start without database service
    docker-compose -f docker-compose.yml up -d --build traefik web
    
else
    echo "❌ Invalid choice. Please run the script again and choose 1 or 2."
    exit 1
fi

# Run migrations
echo "📊 Running database migrations..."
docker-compose -f docker-compose.yml exec web python manage.py migrate_schemas --shared
docker-compose -f docker-compose.yml exec web python manage.py migrate_schemas --tenant

# Create development setup
echo "🔧 Setting up development environment..."
docker-compose -f docker-compose.yml exec web python manage.py setup_development

echo ""
echo "✅ Setup complete! Your Taruvi application is now running with Traefik."
echo ""
echo "🌐 Access URLs:"
echo "   Main App:        http://localhost"
echo "   Admin:          http://localhost/admin/"
echo "   API Docs:       http://localhost/api/docs/"
echo "   Traefik Dashboard: http://localhost:8080"
echo ""
echo "🏢 Tenant Access (create tenants via admin first):"
echo "   Tenant URLs:    http://tenant1.localhost"
echo "                   http://tenant2.localhost"
echo "                   http://[schema-name].localhost"
echo ""
echo "📝 To create a new tenant:"
echo "   1. Go to http://localhost/admin/"
echo "   2. Create a new Client with your desired schema name"
echo "   3. Create a Domain pointing to [schema-name].localhost"
echo "   4. Access your tenant at http://[schema-name].localhost"
echo ""
echo "🔧 Management commands:"
echo "   docker-compose -f docker-compose.traefik.yml logs -f    # View logs"
echo "   docker-compose -f docker-compose.traefik.yml down      # Stop services"
echo "   docker-compose -f docker-compose.traefik.yml restart   # Restart services"
# Getting Started with Taruvi

This guide will help you set up Taruvi for development and create your first multi-tenant application.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13+** - Latest Python version for optimal performance
- **PostgreSQL 13+** - Database with tenant schema support
- **Node.js 20+** - For documentation and frontend assets
- **Docker & Docker Compose** - Optional but recommended for development
- **Git** - Version control system

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/taruvi.git
cd taruvi

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Key settings to configure:
# - DATABASE_URL or individual DB settings
# - SECRET_KEY (generate a secure one for production)
# - DEBUG=True for development
```

Example `.env` file:
```bash
# Database
DB_NAME=taruvi_dev
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Django
SECRET_KEY=your-super-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=127.0.0.1.nip.io,*.127.0.0.1.nip.io,localhost,127.0.0.1

# Celery (for background tasks)
CELERY_BROKER_URL=redis://localhost:6379/0

# AWS (optional for S3 storage)
USE_S3=False
```

### 3. Database Setup

```bash
# Create database
createdb taruvi_dev

# Run migrations for shared schema
python manage.py migrate_schemas --shared

# Run migrations for tenant schemas
python manage.py migrate_schemas --tenant

# Setup development data
python manage.py setup_development
```

The `setup_development` command creates:
- A superuser admin account
- A sample organization
- A test tenant with domain
- Sample users and permissions

### 4. Run Development Server

```bash
# Start Django development server
python manage.py runserver

# Access the application:
# - Platform Admin: http://localhost:8000/admin/
# - API Documentation: http://localhost:8000/api/docs/
# - Health Check: http://localhost:8000/health/
```

## Docker Development (Recommended)

For a more consistent development environment:

```bash
# Start all services
docker-compose up -d

# Initialize database
docker-compose exec web python manage.py migrate_schemas --shared
docker-compose exec web python manage.py migrate_schemas --tenant
docker-compose exec web python manage.py setup_development

# View logs
docker-compose logs -f web
```

Services included:
- **web**: Django application
- **db**: PostgreSQL database  
- **redis**: Cache and Celery broker
- **celery_worker**: Background task processor (with profile)
- **celery_beat**: Periodic task scheduler (with profile)

## Creating Your First Tenant

### Using Django Admin

1. Visit http://localhost:8000/admin/
2. Login with the superuser account created by `setup_development`
3. Navigate to **Core > Sites**
4. Click **Add Site** and fill in:
   - **Name**: Your organization name
   - **Schema name**: Unique identifier (e.g., 'acme')
   - **Description**: Optional description

### Using Management Commands

```bash
# Create a new tenant
python manage.py create_tenant \
  --name "Acme Corporation" \
  --schema "acme" \
  --domain "acme.127.0.0.1.nip.io"

# List all tenants
python manage.py list_tenants

# Access tenant shell
python manage.py tenant_command shell --schema=acme
```

### Testing Multi-Tenancy

Once created, your tenant will be accessible at:
- `http://acme.127.0.0.1.nip.io:8000/admin/`
- `http://acme.127.0.0.1.nip.io:8000/api/`

Each tenant has:
- Isolated database schema
- Separate user management
- Independent admin interface
- Isolated API endpoints

## API Development

Taruvi provides a comprehensive REST API built with Django REST Framework:

### Authentication

```bash
# Get JWT tokens
curl -X POST http://localhost:8000/api/auth/jwt/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Use access token
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/api/organizations/
```

### API Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## Background Tasks

Taruvi uses Celery for background processing:

```bash
# Start Celery worker (if not using Docker)
celery -A taruvi_project worker --loglevel=info

# Start Celery beat scheduler
celery -A taruvi_project beat --loglevel=info

# Monitor tasks in Django admin
# Visit /admin/django_celery_results/taskresult/
```

## Health Monitoring

Check application health:

```bash
# JSON health check
curl http://localhost:8000/health/?format=json

# Plain text check
curl http://localhost:8000/health/
```

Health check includes:
- Database connectivity
- Cache availability
- Storage access
- Celery worker status

## Next Steps

Now that you have Taruvi running:

1. **Explore the Admin**: Navigate through the Django admin to understand the data models
2. **Test the API**: Use the interactive API docs to explore endpoints
3. **Create Organizations**: Set up organizations and invite members
4. **Build Features**: Start adding your application-specific models and views
5. **Deploy**: Check our [Deployment Guide](./deployment.md) for production setup

## Common Issues

### Database Connection
```bash
# Test database connection
python manage.py dbshell
```

### Schema Issues
```bash
# Check migrations
python manage.py showmigrations

# Reset tenant schemas (development only)
python manage.py migrate_schemas --tenant --fake-initial
```

### Port Conflicts
If port 8000 is busy:
```bash
python manage.py runserver 8080
# Then use 127.0.0.1.nip.io:8080 in URLs
```

Ready to dive deeper? Check out our [Architecture Guide](./architecture.md) or [API Documentation](./api/overview.md).
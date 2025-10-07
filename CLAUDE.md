# TARUVI - Enterprise Django SaaS Platform

## Overview
Taruvi is a multi-tenant Software-as-a-Service (SaaS) platform built with Django 5.2.6, designed for enterprise-grade applications. The platform allows organizations to create isolated projects/sites with their own users, while maintaining shared infrastructure and administration.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Multi-Tenancy Implementation](#multi-tenancy-implementation)
4. [Project Structure](#project-structure)
5. [Configuration Files](#configuration-files)
6. [Database Architecture](#database-architecture)
7. [User Hierarchy & Authentication](#user-hierarchy--authentication)
8. [API & Documentation](#api--documentation)
9. [Background Tasks (Celery)](#background-tasks-celery)
10. [Monitoring & Logging](#monitoring--logging)
11. [Development Setup](#development-setup)
12. [Production Deployment](#production-deployment)
13. [Admin Interface](#admin-interface)
14. [Security Features](#security-features)
15. [AWS Integration](#aws-integration)
16. [Troubleshooting](#troubleshooting)

## Architecture Overview

### High-Level Architecture
```
┌─────────────────────────────────────────────────────┐
│                 Platform Level                       │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │   Django Admin  │  │   API Gateway   │          │
│  │   (Shared)      │  │   (DRF + JWT)   │          │
│  └─────────────────┘  └─────────────────┘          │
│                                                     │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │     Celery      │  │   Monitoring    │          │
│  │   (SQS + DB)    │  │  (Health/Logs)  │          │
│  └─────────────────┘  └─────────────────┘          │
└─────────────────────────────────────────────────────┘
                         │
                         │ Multi-Tenant Layer
                         ▼
┌─────────────────────────────────────────────────────┐
│                Project Level                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  Project A  │  │  Project B  │  │  Project C  │ │
│  │ (Schema A)  │  │ (Schema B)  │  │ (Schema C)  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Core Principles
1. **Multi-Tenancy**: Each project gets isolated database schema
2. **Shared Infrastructure**: Common services (auth, admin, celery) shared across all projects
3. **API-First**: RESTful APIs with comprehensive documentation
4. **Enterprise Security**: JWT authentication, rate limiting, security headers
5. **Scalability**: SQS-based task processing, local/Redis caching options
6. **Monitoring**: Comprehensive logging, health checks, OpenTelemetry ready

## Technology Stack

### Core Framework
- **Django 5.2.6**: Latest LTS web framework
- **Python 3.13**: Latest Python version
- **PostgreSQL**: Primary database with tenant schema support
- **Django Tenants**: Multi-tenant implementation

### API & Authentication
- **Django REST Framework**: API development
- **SimpleJWT**: JWT token authentication
- **drf-spectacular**: OpenAPI/Swagger documentation
- **CORS**: Cross-origin request support

### Background Processing
- **Celery 5.5.3**: Distributed task queue
- **Amazon SQS**: Message broker for production
- **Django Database**: Results backend
- **Django Celery Beat**: Periodic task scheduling

### Infrastructure & DevOps
- **AWS S3**: File storage with CloudFront CDN
- **Docker & Docker Compose**: Containerization
- **WhiteNoise**: Static file serving
- **Gunicorn**: WSGI application server

### Monitoring & Security
- **Django Health Check**: Application health monitoring
- **OpenTelemetry**: Distributed tracing (optional)
- **Sentry**: Error tracking (optional)
- **Rate Limiting**: API protection
- **Security Headers**: OWASP security compliance

### Admin & UI
- **Django Jazzmin**: Modern admin interface theme
- **FontAwesome**: Icons and UI elements

## Multi-Tenancy Implementation

### Tenant Architecture
The platform uses **schema-based multi-tenancy** via `django-tenants`:

#### Shared Schema (Platform Level)
- **Purpose**: Stores platform-wide data and tenant management
- **Location**: `public` PostgreSQL schema
- **Contains**: 
  - Client/Domain models (tenant definitions)
  - Platform admin users
  - Shared infrastructure data
  - Celery task scheduling

#### Tenant Schemas (Project Level)
- **Purpose**: Isolated data per project/client
- **Location**: Individual PostgreSQL schemas per tenant
- **Contains**:
  - Project-specific users and permissions
  - Project business data
  - Project-specific content types
  - Project sessions

#### Implementation Files:
1. **`core/models.py`**: Tenant models and BaseModel
```python
from django_tenants.models import TenantMixin, DomainMixin
from django.contrib.auth.models import User

class BaseModel(models.Model):
    """Abstract base model with common fields for all models"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_%(class)s_set')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='modified_%(class)s_set')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_%(class)s_set')
    
    class Meta:
        abstract = True
        ordering = ['-created_at']

class Client(TenantMixin):
    name = CharField(max_length=100)
    created_on = DateField(auto_now_add=True)
    is_active = BooleanField(default=True)
    auto_create_schema = True  # Automatic schema creation

class Domain(DomainMixin):
    pass
```

2. **Settings Configuration**:
```python
# Tenant Configuration
TENANT_MODEL = "core.Client"
TENANT_DOMAIN_MODEL = "core.Domain"
DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)

# Apps Distribution
SHARED_APPS = [...]  # Platform infrastructure
TENANT_APPS = [...]  # Project-specific apps
```

## Project Structure

```
taruvi/
├── taruvi_project/          # Django project directory
│   ├── __init__.py
│   ├── settings.py          # Main configuration file
│   ├── urls.py             # URL routing
│   ├── wsgi.py             # WSGI configuration
│   ├── celery.py           # Celery configuration
│   ├── middleware.py       # Custom middleware
│   └── tracing.py          # OpenTelemetry setup
├── core/                   # Core application
│   ├── models.py           # Tenant models (Client, Domain)
│   ├── admin.py            # Admin interface configuration
│   ├── views.py            # API views
│   ├── urls.py             # Core URL patterns
│   ├── tasks.py            # Celery tasks
│   ├── decorators.py       # Custom decorators
│   └── management/         # Management commands
│       └── commands/
│           └── setup_development.py
├── static/                 # Static files
├── media/                  # Media files (development)
├── templates/              # Template files
├── logs/                   # Application logs
├── requirements.txt        # Python dependencies
├── manage.py              # Django management script
├── .env                   # Environment variables
├── .env.example           # Environment template
├── docker-compose.yml     # Development containers
├── docker-compose.prod.yml # Production containers
├── docker-compose.observability.yml # Monitoring stack
├── Dockerfile             # Application container
├── README.md              # Setup documentation
├── PRODUCTION.md          # Production deployment guide
└── CLAUDE.md              # This documentation file
```

## Configuration Files

### 1. Environment Configuration (`.env`)

#### Core Django Settings
```bash
SECRET_KEY=django-insecure-development-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

#### Database Configuration
```bash
DB_NAME=taruvi
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

#### Celery Configuration
```bash
CELERY_BROKER_URL=sqs://
CELERY_RESULT_BACKEND=django-db
CELERY_QUEUE_PREFIX=taruvi-
```

#### AWS Configuration
```bash
USE_S3=False
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID_HERE
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY_HERE
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-2
```

### 2. Django Settings (`taruvi_project/settings.py`)

#### Multi-Tenant Configuration
```python
# Tenant Models
TENANT_MODEL = "core.Client"
TENANT_DOMAIN_MODEL = "core.Domain"

# Database Router
DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)

# App Distribution
SHARED_APPS = [
    'django_tenants',
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    # ... platform infrastructure
]

TENANT_APPS = [
    'django.contrib.auth',          # Project users
    'django.contrib.contenttypes',  # Project content types
    'django.contrib.sessions',      # Project sessions
    # ... future project-specific apps
]
```

#### Middleware Stack
```python
MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",  # Tenant routing
    "taruvi_project.middleware.CorrelationIdMiddleware",   # Request tracing
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "taruvi_project.middleware.SecurityLoggingMiddleware",  # Security logging
    "taruvi_project.middleware.APILoggingMiddleware",       # API logging
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]
```

## Database Architecture

### Schema Structure

#### Public Schema (Shared)
```sql
-- Tenant Management
core_client (
    schema_name VARCHAR(63) PRIMARY KEY,
    name VARCHAR(100),
    created_on DATE,
    is_active BOOLEAN
);

core_domain (
    domain VARCHAR(253) PRIMARY KEY,
    tenant_id VARCHAR(63) REFERENCES core_client(schema_name),
    is_primary BOOLEAN
);

-- Celery Infrastructure
django_celery_beat_periodictask (...);
django_celery_results_taskresult (...);

-- Platform Users
auth_user (...);
```

#### Tenant Schemas (Per Project)
```sql
-- Each tenant gets their own schema: client1, client2, etc.
-- Project-specific data
auth_user (...)              -- Project users
auth_group (...)             -- Project groups/roles
auth_permission (...)        -- Project permissions

-- Future project apps will create tables here
-- projects_project (...)
-- tasks_task (...)
-- files_document (...)
```

### Migration Strategy
```python
# Shared migrations
python manage.py migrate_schemas --shared

# Tenant migrations
python manage.py migrate_schemas --tenant

# Development setup
python manage.py setup_development
```

## User Hierarchy & Authentication

### User Types

#### 1. Platform Admins (Superusers)
- **Location**: Shared schema
- **Access**: Full platform control via `/admin/`
- **Capabilities**:
  - Create/manage all clients/projects
  - Access all system monitoring
  - Manage platform-wide settings
  - Control Celery tasks globally

#### 2. Organization Admins
- **Location**: Shared schema (can access multiple tenants)
- **Access**: Project-specific admin via `project.domain.com/admin/`
- **Capabilities**:
  - Create and configure their projects
  - Manage project users
  - Configure project settings
  - Access project-specific data

#### 3. Project Users
- **Location**: Tenant schema (project-specific)
- **Access**: API and project-specific interfaces
- **Capabilities**:
  - Work within assigned project
  - Access project data based on permissions
  - Use project features and tools

### Authentication Flow

#### JWT Token Authentication
```python
# Settings Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# API Authentication Classes
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
}
```

#### API Endpoints
```
POST /api/auth/jwt/token/          # Obtain JWT tokens
POST /api/auth/jwt/token/refresh/  # Refresh access token
POST /api/auth/jwt/token/blacklist/ # Blacklist refresh token
```

## API & Documentation

### API Framework
- **Base**: Django REST Framework
- **Documentation**: drf-spectacular (OpenAPI 3.0)
- **Authentication**: JWT + Session + Token auth
- **Permissions**: Configurable per endpoint

### API Documentation
- **Swagger UI**: `/api/docs/` (interactive documentation)
- **ReDoc**: `/api/redoc/` (alternative documentation view)
- **OpenAPI Schema**: `/api/schema/` (JSON schema)

### API Configuration
```python
# DRF Spectacular Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Taruvi API',
    'DESCRIPTION': 'Enterprise Django SaaS Platform API',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],  # Open for development
    'SERVE_AUTHENTICATION': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}
```

### Rate Limiting
```python
# Configuration
RATE_LIMIT_ENABLE = True
API_RATE_LIMIT_PER_MINUTE = 100
API_RATE_LIMIT_BURST = 10

# Decorator Usage
@api_rate_limit()
@burst_rate_limit()
def api_view(request):
    # Rate limited endpoint
```

## Background Tasks (Celery)

### Architecture
- **Broker**: Amazon SQS (production) / Django DB (development)
- **Results Backend**: Django Database
- **Scheduler**: Django Celery Beat (database-backed)
- **Monitoring**: Django Admin interface

### Configuration
```python
# Celery Settings
CELERY_BROKER_URL = 'sqs://'
CELERY_RESULT_BACKEND = 'django-db'

# SQS Configuration
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'region': 'us-east-2',
    'visibility_timeout': 300,
    'polling_interval': 0.3,
    'queue_name_prefix': 'taruvi-',
}
```

### Task Examples (`core/tasks.py`)
```python
@shared_task(bind=True)
def send_email_task(self, subject, message, recipient_list):
    """Send email with retry logic"""
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)
        return f"Email sent to {len(recipient_list)} recipients"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@periodic_task(run_every=crontab(minute=0, hour='*/6'))
def cleanup_old_sessions():
    """Clean up old sessions every 6 hours"""
    call_command('clearsessions')
```

### Admin Management
- **Periodic Tasks**: Schedule recurring jobs via Django admin
- **Task Results**: Monitor task execution and results
- **Cron/Interval Schedules**: Configure timing patterns
- **Task History**: View execution logs and performance

## Monitoring & Logging

### Health Checks
- **Endpoint**: `/health/?format=json`
- **Components**: Database, cache, storage, Celery
- **Libraries**: django-health-check

### Logging System
```python
# Structured JSON Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'taruvi_project.settings.JSONFormatter',
        },
    },
    'loggers': {
        'django': {...},
        'celery': {...},
        'security': {...},
        'api': {...},
    },
}
```

### Log Files
- **django.log**: General application logs
- **celery.log**: Task processing logs
- **security.log**: Security-related events
- **api.log**: API request/response logs

### Middleware Logging
```python
# Custom Middleware
CorrelationIdMiddleware    # Request tracing
SecurityLoggingMiddleware  # Security event logging
APILoggingMiddleware      # API access logging
```

### Optional Integrations
- **OpenTelemetry**: Distributed tracing
- **Sentry**: Error tracking and performance monitoring
- **Prometheus**: Metrics collection

## Development Setup

### Prerequisites
```bash
# System Requirements
Python 3.13+
PostgreSQL 13+
Redis (optional, for production-like caching)
Docker & Docker Compose (optional)
```

### Quick Start
```bash
# 1. Clone and setup virtual environment
git clone <repository>
cd taruvi
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Environment setup
cp .env.example .env
# Edit .env with your database credentials

# 4. Database setup
createdb taruvi
python manage.py migrate_schemas
python manage.py setup_development

# 5. Run development server
python manage.py runserver
```

### Docker Development
```bash
# Start all services
docker-compose up -d

# Initialize database
docker-compose exec web python manage.py migrate_schemas
docker-compose exec web python manage.py setup_development

# Access services
# - Django: http://localhost:8000
# - Admin: http://localhost:8000/admin/
# - API Docs: http://localhost:8000/api/docs/
```

### Management Commands
```bash
# Development setup
python manage.py setup_development

# Create tenants
python manage.py create_tenant --name "Test Company" --schema "test"

# List tenants
python manage.py list_tenants

# Health checks
curl http://localhost:8000/health/?format=json
```

## Production Deployment

### Environment Preparation
```bash
# Production environment variables
DEBUG=False
SECRET_KEY=<50+ character secure key>
ALLOWED_HOSTS=your-domain.com

# Database
DB_NAME=taruvi_production
DB_USER=taruvi_prod
DB_PASSWORD=<secure-password>
DB_HOST=<rds-endpoint>

# Celery SQS
CELERY_BROKER_URL=sqs://
AWS_ACCESS_KEY_ID=<access-key>
AWS_SECRET_ACCESS_KEY=<secret-key>

# S3 Storage
USE_S3=True
AWS_STORAGE_BUCKET_NAME=<bucket-name>
AWS_S3_REGION_NAME=us-east-2
```

### Docker Production
```bash
# Build production image
docker build -f Dockerfile -t taruvi:latest .

# Deploy with production compose
docker-compose -f docker-compose.prod.yml up -d

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker=4
```

### Traditional Deployment
```bash
# Install system dependencies
sudo apt update && sudo apt install -y python3.11 nginx postgresql-client

# Create app user and directories
sudo adduser --system --group taruvi
sudo mkdir -p /opt/taruvi
sudo chown taruvi:taruvi /opt/taruvi

# Deploy application
sudo -u taruvi git clone <repository> /opt/taruvi
cd /opt/taruvi
sudo -u taruvi python3.11 -m venv venv
sudo -u taruvi ./venv/bin/pip install -r requirements.txt

# Configure services
# - Gunicorn: WSGI server
# - Nginx: Reverse proxy
# - Supervisor: Process management
```

### Security Checklist
- [ ] SSL/TLS certificates configured
- [ ] Security headers enabled
- [ ] Database connections encrypted
- [ ] Secret key rotated
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Monitoring and logging active

## Admin Interface

### Platform Admin (`/admin/`)
**Access**: Platform administrators
**Features**:
- Modern Jazzmin theme with custom branding
- Client/Project management
- Domain configuration
- Celery task monitoring
- User management
- System health monitoring

### Admin Configuration (`core/admin.py`)
```python
@admin.register(Client)
class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'created_on', 'is_active')
    list_filter = ('created_on', 'is_active')
    search_fields = ('name', 'schema_name')
    readonly_fields = ('schema_name', 'created_on')
```

### Jazzmin Configuration
```python
JAZZMIN_SETTINGS = {
    "site_title": "Taruvi Admin",
    "site_header": "Taruvi",
    "site_brand": "Taruvi",
    "welcome_sign": "Welcome to Taruvi Admin",
    # Custom navigation and theming
}
```

### Admin Features
- **Search**: Global search across models
- **Filtering**: Advanced filtering options
- **Actions**: Bulk operations on records
- **Custom Links**: Direct access to API docs and health checks
- **Icons**: FontAwesome icons for visual clarity

## Security Features

### Authentication & Authorization
```python
# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

### Security Middleware
```python
# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# HTTPS (Production)
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### Rate Limiting
```python
# Decorators
@api_rate_limit()         # Standard API rate limit
@burst_rate_limit()       # Burst protection
@auth_rate_limit()        # Authentication endpoint protection

# Configuration
RATE_LIMIT_ENABLE = True
API_RATE_LIMIT_PER_MINUTE = 100
API_RATE_LIMIT_BURST = 10
```

### Security Logging
```python
# Automatic detection of:
- Suspicious user agents
- Path traversal attempts
- Script injection attempts
- Authentication failures
- Rate limit violations
```

## AWS Integration

### S3 Storage
```python
# Configuration
if USE_S3:
    AWS_STORAGE_BUCKET_NAME = 'your-bucket'
    AWS_S3_REGION_NAME = 'us-east-2'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
```

### SQS Message Broker
```python
# Celery SQS Configuration
CELERY_BROKER_URL = 'sqs://'
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'region': 'us-east-2',
    'visibility_timeout': 300,
    'polling_interval': 0.3,
    'queue_name_prefix': 'taruvi-',
}
```

### CloudFront CDN
```python
# Static file acceleration
AWS_S3_CUSTOM_DOMAIN = 'd123456.cloudfront.net'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
```

## Troubleshooting

### Common Issues

#### 1. Tenant Creation Issues
```bash
# Check tenant setup
python manage.py list_tenants

# Create development tenant
python manage.py setup_development
```

#### 2. Database Connection Issues
```bash
# Test database connection
python manage.py dbshell

# Check migrations
python manage.py showmigrations
```

#### 3. Static Files Issues
```bash
# Collect static files
python manage.py collectstatic --noinput

# Check S3 configuration
python manage.py shell -c "from django.core.files.storage import default_storage; print(default_storage)"
```

#### 4. Celery Issues
```bash
# Test Celery connection
python manage.py shell -c "from celery import current_app; print(current_app.control.inspect().stats())"

# Check SQS configuration
# Ensure AWS credentials are properly set
```

#### 5. Admin Interface Issues
```bash
# Check if jazzmin is installed
pip list | grep jazzmin

# Verify INSTALLED_APPS order
# jazzmin must be before django.contrib.admin
```

### Debug Commands
```bash
# Django system check
python manage.py check
python manage.py check --deploy

# Database integrity
python manage.py migrate_schemas --shared
python manage.py migrate_schemas --tenant

# Tenant operations
python manage.py tenant_command shell  # Access tenant shell
python manage.py all_tenants_command migrate  # Run command on all tenants
```

### Performance Monitoring
```bash
# Health checks
curl http://localhost:8000/health/?format=json

# API endpoint testing
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/

# Database queries
# Enable Django Debug Toolbar in development
```

### Log Analysis
```bash
# View logs
tail -f logs/django.log
tail -f logs/celery.log
tail -f logs/security.log

# Search for errors
grep -i error logs/*.log
grep -i "correlation_id" logs/api.log
```

## Prompt Instructions for Claude

### Context Understanding
When working with this project, understand that:

1. **Multi-Tenant SaaS**: This is a schema-based multi-tenant application
2. **Enterprise Grade**: Focus on security, scalability, and maintainability
3. **AWS Integration**: Production deployment uses AWS services
4. **API-First**: All functionality should be API-accessible
5. **Admin Interface**: Django admin is heavily customized with Jazzmin

### Key Commands to Remember
```bash
# Always use these for development:
python manage.py setup_development        # Initialize dev environment
python manage.py migrate_schemas --shared # Platform migrations
python manage.py migrate_schemas --tenant # Project migrations
python manage.py list_tenants             # Check tenant status

# For production:
python manage.py check --deploy           # Production readiness
python manage.py collectstatic --noinput  # Static file collection
```

### When Making Changes
1. **Always consider multi-tenancy**: Will this affect shared or tenant data?
2. **Check both app lists**: Ensure apps are in correct SHARED_APPS or TENANT_APPS
3. **Test with tenants**: Create test tenant to verify functionality
4. **Update documentation**: Keep CLAUDE.md current with changes
5. **Consider migrations**: Plan migration strategy for tenant vs shared

### BaseModel Usage

The project includes a `BaseModel` abstract class with common audit trail fields:

#### BaseModel Fields
```python
class BaseModel(models.Model):
    # Timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # User tracking fields
    created_by = models.ForeignKey(User, ...)     # Who created this record
    modified_by = models.ForeignKey(User, ...)    # Who last modified this record  
    assigned_to = models.ForeignKey(User, ...)    # Who this record is assigned to
```

#### Usage in Models
```python
# Instead of this:
class MyModel(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    # ... more boilerplate

# Use this:
class MyModel(BaseModel):
    name = models.CharField(max_length=100)
    # BaseModel fields are automatically included
```

#### Admin Integration
```python
# Use BaseModelAdmin for automatic user tracking
@admin.register(MyModel)
class MyModelAdmin(BaseModelAdmin):
    list_display = ('name', 'assigned_to', 'updated_at')
    # created_by and modified_by are automatically populated
```

#### Features
- **Automatic ordering**: Records sorted by creation date (newest first)
- **User tracking**: Automatically populated in admin interface
- **Nullable fields**: All user fields are optional to handle system records
- **Dynamic relations**: Uses `%(class)s` to avoid relation name conflicts
- **Query optimization**: BaseModelAdmin includes `select_related` for user fields

### File Locations to Remember
- **Settings**: `taruvi_project/settings.py`
- **Models**: `core/models.py` (BaseModel and tenant models)
- **Admin**: `core/admin.py` (BaseModelAdmin and customizations)
- **Tasks**: `core/tasks.py` (Celery tasks)
- **URLs**: `core/urls.py` and `taruvi_project/urls.py`
- **Environment**: `.env` (development) and `.env.example` (template)

This documentation should be kept up-to-date as the project evolves. Any significant changes to architecture, configuration, or functionality should be reflected here.

---

**Last Updated**: [Current Date]  
**Project Version**: 1.0.0  
**Django Version**: 5.2.6  
**Python Version**: 3.13+
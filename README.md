# Taruvi - Enterprise Django SaaS Platform

A production-ready Django application with multi-tenancy, enterprise authentication, observability, and comprehensive security features.

## 🚀 Enterprise Features

### Core Platform
- **Multi-Tenancy**: Complete tenant isolation using `django-tenants`
- **JWT Authentication**: Production-ready JWT with refresh tokens
- **Social Authentication**: Ready for Google, GitHub (django-allauth)
- **API Documentation**: Auto-generated OpenAPI 3.0 docs with Swagger UI
- **Advanced Security**: Rate limiting, CORS, security headers, audit logging

### Observability & Monitoring
- **OpenTelemetry**: Distributed tracing with auto-instrumentation
- **Structured Logging**: JSON logs with correlation IDs and log rotation
- **Health Checks**: Comprehensive health endpoints for K8s/Docker
- **Prometheus Metrics**: Application and business metrics
- **Error Tracking**: Sentry integration
- **Monitoring Stack**: Grafana + Prometheus + Jaeger + Loki (optional)

### Background Processing
- **Celery**: Asynchronous task processing with Redis
- **Task Management**: Built-in task monitoring and retry logic
- **Periodic Tasks**: Celery Beat with database scheduler

### Cloud & Storage
- **AWS S3**: Production file storage with CloudFront support
- **Database**: PostgreSQL with tenant-aware schemas
- **Caching**: Redis for sessions and ORM query caching
- **Docker**: Multi-stage builds with observability stack

### Performance & Security
- **Rate Limiting**: Per-user/IP API rate limiting
- **Response Caching**: Redis-backed API response caching
- **Security Headers**: CSP, HSTS, XSS protection
- **Audit Logging**: Security events and API access logs

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Docker & Docker Compose (for containerized setup)
- AWS S3 (optional, for cloud storage)

## 🛠️ Quick Start

### Option 1: Docker Setup (Recommended)

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd Taruvi
   cp .env.example .env
   # Edit .env with your configurations
   ```

2. **Basic Development Setup**
   ```bash
   # Core services only (Django, PostgreSQL, Redis, Celery)
   docker-compose up -d
   ```

3. **With Full Observability Stack** (Optional)
   ```bash
   # Include Prometheus, Grafana, Jaeger, Loki
   docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d
   ```

4. **Initialize Database**
   ```bash
   # Run migrations (this will create the public tenant automatically)
   docker-compose exec web python manage.py migrate_schemas
   
   # Set up development environment (creates public tenant, localhost domain, and admin user)
   docker-compose exec web python manage.py setup_development
   
   # Create additional tenants (optional)
   docker-compose exec web python manage.py create_tenant \
     --name "Test Company" --schema "test" --domain "test.localhost"
   ```

### Option 2: Local Development Setup

1. **Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Setup**
   ```bash
   # Create PostgreSQL database
   createdb taruvi
   
   # Run migrations (creates public tenant automatically)
   python manage.py migrate_schemas
   
   # Set up development environment
   python manage.py setup_development
   ```

4. **Start Services**
   ```bash
   # Terminal 1: Django
   python manage.py runserver
   
   # Terminal 2: Celery Worker
   celery -A taruvi_project worker --loglevel=info
   
   # Terminal 3: Celery Beat (optional)
   celery -A taruvi_project beat --loglevel=info
   ```

## 🏗️ Architecture

### Multi-Tenancy
- **Shared Apps**: Core functionality shared across all tenants
- **Tenant Apps**: Isolated data and functionality per tenant
- **Schema Separation**: Each tenant has its own PostgreSQL schema

### Background Tasks
- **Celery Workers**: Process background tasks asynchronously
- **Redis Broker**: Message queue for task distribution
- **Celery Beat**: Scheduled/periodic task execution

### Storage
- **Local Development**: File system storage
- **Production**: AWS S3 with CloudFront CDN support

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

#### Core Django Settings
```bash
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
```

#### Database
```bash
DB_NAME=taruvi_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
```

#### Celery & Redis
```bash
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

#### AWS S3 (Optional)
```bash
USE_S3=False
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=us-east-1
```

## 👥 Multi-Tenant Usage

### Creating Tenants

1. **Using Django Admin**
   - Access `/admin/`
   - Create a new Client (tenant)
   - Add a Domain pointing to the tenant

2. **Using Management Commands**
   ```bash
   # Create tenant programmatically
   python manage.py shell
   ```
   ```python
   from core.models import Client, Domain
   
   # Create tenant
   tenant = Client(schema_name='tenant1', name='Tenant 1')
   tenant.save()
   
   # Add domain
   domain = Domain(domain='tenant1.localhost', tenant=tenant, is_primary=True)
   domain.save()
   ```

### Accessing Tenants
- **Public Schema**: `localhost:8000` (shared/public data)
- **Tenant Schema**: `tenant1.localhost:8000` (tenant-specific data)

## 🔄 Celery Tasks

### Available Tasks
- `debug_task()`: Simple test task
- `send_email_task(subject, message, recipients)`: Send emails
- `process_data_task(data)`: Data processing example
- `cleanup_old_data()`: Periodic cleanup task

### Running Tasks
```python
from core.tasks import send_email_task

# Async execution
result = send_email_task.delay('Subject', 'Message', ['user@example.com'])

# Check status
print(result.status)
print(result.result)
```

### Monitoring
- **Flower**: Access `http://localhost:5555` (production setup)
- **Logs**: Check Celery worker logs for task execution

## 🐳 Docker Commands

### Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f web
docker-compose logs -f celery_worker

# Execute commands
docker-compose exec web python manage.py migrate_schemas
docker-compose exec web python manage.py shell

# Stop services
docker-compose down
```

### Production
```bash
# Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker=3
```

## 📊 Monitoring & Health Checks

### Health Endpoints
- **Application**: `http://localhost:8000/health/` (implement if needed)
- **Celery Flower**: `http://localhost:5555/` (production)
- **Database**: Built-in Docker health checks

### Logs
- **Django**: Console + `django.log` file
- **Celery**: Console output with structured logging
- **Docker**: `docker-compose logs -f <service>`

## 🚀 Deployment

### Production Checklist
1. Set `DEBUG=False` in environment
2. Configure proper `SECRET_KEY`
3. Set up SSL certificates
4. Configure domain names
5. Set up monitoring and alerting
6. Configure backup strategy
7. Set up log aggregation

### AWS Deployment
1. Set up RDS PostgreSQL instance
2. Set up ElastiCache Redis cluster
3. Configure S3 bucket with CloudFront
4. Use ECS/EKS for container orchestration
5. Set up Application Load Balancer

## 🧪 Testing

```bash
# Run tests
python manage.py test

# With pytest
pytest

# Coverage
coverage run --source='.' manage.py test
coverage report
```

## 📝 API Documentation

### Authentication
- Token-based authentication
- Session authentication for web interface

### Endpoints
- `/api/auth/`: Authentication endpoints
- `/api/v1/`: Main API endpoints (implement as needed)
- `/admin/`: Django admin interface

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Common Issues
1. **Port conflicts**: Ensure ports 8000, 5432, 6379 are available
2. **Permission errors**: Check file permissions and user groups
3. **Database connections**: Verify PostgreSQL is running and accessible
4. **Celery not processing**: Check Redis connection and worker status

### Getting Help
- Check application logs: `docker-compose logs -f web`
- Check Celery logs: `docker-compose logs -f celery_worker`
- Verify environment variables in `.env`
- Ensure all required services are running

### Development Tips
- Use `django-debug-toolbar` for SQL query optimization
- Monitor Celery tasks with Flower
- Use `python manage.py shell_plus` for enhanced shell
- Check tenant schemas with `python manage.py show_urls --settings=myapp.settings`

---

**Built with ❤️ using Django, Celery, PostgreSQL, and Redis**
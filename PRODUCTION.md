# Production Deployment Guide

This guide covers deploying the Taruvi Django enterprise application to production environments.

## 🏗️ Production Architecture

### Infrastructure Components
- **Web Server**: Gunicorn + Nginx reverse proxy
- **Database**: PostgreSQL 13+ with read replicas
- **Cache**: Redis Cluster for caching and Celery broker
- **Storage**: AWS S3 + CloudFront CDN
- **Monitoring**: Prometheus, Grafana, Jaeger, Sentry
- **Load Balancer**: AWS Application Load Balancer or Nginx

### Recommended AWS Services
- **Compute**: ECS Fargate or EKS
- **Database**: RDS PostgreSQL Multi-AZ
- **Cache**: ElastiCache Redis Cluster
- **Storage**: S3 + CloudFront
- **Secrets**: AWS Secrets Manager
- **Monitoring**: CloudWatch + Custom metrics

## 📋 Pre-Deployment Checklist

### Environment Configuration
- [ ] Set `DEBUG=False`
- [ ] Configure production `SECRET_KEY` (minimum 50 characters)
- [ ] Set up proper `ALLOWED_HOSTS`
- [ ] Configure SSL certificates
- [ ] Set up domain names and DNS
- [ ] Configure environment variables for all services

### Security Requirements
- [ ] Enable HTTPS/SSL redirect
- [ ] Configure security headers (HSTS, CSP, etc.)
- [ ] Set up CORS policies
- [ ] Configure rate limiting
- [ ] Set up Sentry error tracking
- [ ] Enable audit logging

### Database Setup
- [ ] Create production PostgreSQL instance
- [ ] Set up database backups
- [ ] Configure connection pooling
- [ ] Set up read replicas (optional)
- [ ] Test database migrations

### Dependencies
- [ ] Set up Redis cluster
- [ ] Configure S3 bucket and IAM policies
- [ ] Set up CloudFront distribution
- [ ] Configure monitoring stack

## 🚀 Deployment Methods

### Option 1: Docker Container Deployment

#### 1. Build Production Image
```bash
# Build optimized production image
docker build -f Dockerfile.prod -t taruvi:latest .

# Tag for registry
docker tag taruvi:latest your-registry.com/taruvi:v1.0.0
```

#### 2. Deploy with Docker Compose (Single Server)
```bash
# Production compose file
docker-compose -f docker-compose.prod.yml up -d

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker=4
```

#### 3. Deploy to AWS ECS/Fargate
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com

docker build -f Dockerfile.prod -t taruvi .
docker tag taruvi:latest your-account.dkr.ecr.us-east-1.amazonaws.com/taruvi:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/taruvi:latest
```

### Option 2: Traditional Server Deployment

#### 1. Server Setup (Ubuntu 22.04)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv nginx postgresql-client redis-tools supervisor

# Create app user
sudo adduser --system --group --shell /bin/bash taruvi
sudo mkdir -p /opt/taruvi
sudo chown taruvi:taruvi /opt/taruvi
```

#### 2. Application Setup
```bash
# Switch to app user
sudo su - taruvi

# Clone repository
cd /opt/taruvi
git clone <repository-url> .

# Setup virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate_schemas
```

#### 3. Gunicorn Configuration
Create `/opt/taruvi/gunicorn.conf.py`:
```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
keepalive = 5
timeout = 30
graceful_timeout = 10
```

#### 4. Supervisor Configuration
Create `/etc/supervisor/conf.d/taruvi.conf`:
```ini
[program:taruvi-web]
command=/opt/taruvi/venv/bin/gunicorn taruvi_project.wsgi:application -c /opt/taruvi/gunicorn.conf.py
directory=/opt/taruvi
user=taruvi
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/taruvi/gunicorn.log

[program:taruvi-celery]
command=/opt/taruvi/venv/bin/celery -A taruvi_project worker --loglevel=info --concurrency=4
directory=/opt/taruvi
user=taruvi
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/taruvi/celery.log

[program:taruvi-celery-beat]
command=/opt/taruvi/venv/bin/celery -A taruvi_project beat --loglevel=info
directory=/opt/taruvi
user=taruvi
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/taruvi/celery-beat.log
```

#### 5. Nginx Configuration
Create `/etc/nginx/sites-available/taruvi`:
```nginx
upstream taruvi {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100M;
    keepalive_timeout 5;

    location / {
        proxy_pass http://taruvi;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /static/ {
        alias /opt/taruvi/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /health/ {
        proxy_pass http://taruvi;
        access_log off;
    }
}
```

## 🔧 Production Configuration

### Environment Variables (.env.production)
```bash
# Core Django
SECRET_KEY=your-super-secret-production-key-minimum-50-characters
DEBUG=False
ALLOWED_HOSTS=your-domain.com,api.your-domain.com

# Database
DB_NAME=taruvi_production
DB_USER=taruvi_prod_user
DB_PASSWORD=super-secure-db-password
DB_HOST=your-rds-endpoint.amazonaws.com
DB_PORT=5432

# Redis
CELERY_BROKER_URL=redis://your-elasticache-endpoint:6379/0
CELERY_RESULT_BACKEND=redis://your-elasticache-endpoint:6379/0
REDIS_URL=redis://your-elasticache-endpoint:6379/1

# AWS S3
USE_S3=True
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=taruvi-production-media
AWS_S3_REGION_NAME=us-east-1
AWS_S3_CUSTOM_DOMAIN=d123456.cloudfront.net

# OpenTelemetry
OTEL_ENABLED=True
OTEL_SERVICE_NAME=taruvi-production
OTEL_SERVICE_VERSION=1.0.0
OTEL_EXPORTER_TYPE=jaeger
OTEL_EXPORTER_JAEGER_ENDPOINT=http://your-jaeger-endpoint:14268/api/traces

# Monitoring
SENTRY_ENABLED=True
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
PROMETHEUS_METRICS_ENABLED=True
HEALTH_CHECKS_ENABLED=True

# Security
RATE_LIMIT_ENABLE=True
SECURITY_HEADERS_ENABLE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## 📊 Monitoring Setup

### Prometheus Configuration
Create `/opt/monitoring/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'taruvi-django'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics/'
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
```

### Grafana Dashboard Import
- Django metrics dashboard: ID 9528
- PostgreSQL dashboard: ID 9628
- Redis dashboard: ID 763
- System metrics dashboard: ID 1860

### Log Aggregation
```bash
# Install Fluentd or similar
curl -L https://toolbelt.treasuredata.com/sh/install-ubuntu-jammy-td-agent4.sh | sh

# Configure log forwarding to ELK stack or CloudWatch
```

## 🔄 Database Management

### Backup Strategy
```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/opt/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="taruvi_production"

mkdir -p $BACKUP_DIR

# Create backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME | gzip > $BACKUP_DIR/taruvi_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "taruvi_*.sql.gz" -mtime +30 -delete

# Upload to S3
aws s3 cp $BACKUP_DIR/taruvi_$DATE.sql.gz s3://your-backup-bucket/database/
```

### Migration Strategy
```bash
# Zero-downtime migrations
python manage.py migrate_schemas --shared --parallel 4

# For each tenant (if needed)
python manage.py migrate_schemas --tenant
```

## 📈 Performance Optimization

### Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_tenant_created_at ON tenant_table(created_at);
CREATE INDEX CONCURRENTLY idx_user_last_login ON auth_user(last_login) WHERE last_login IS NOT NULL;

-- Connection pooling settings
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

### Application Optimization
```python
# settings_production.py
CONN_MAX_AGE = 300  # Database connection pooling
CACHALOT_ENABLED = True  # ORM query caching

# Celery optimization
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
```

## 🛡️ Security Hardening

### System Security
```bash
# Firewall rules
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Fail2ban for SSH
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### Application Security
- Enable WAF (Web Application Firewall)
- Configure DDoS protection
- Regular security audits with `safety` and `bandit`
- Keep dependencies updated
- Monitor for vulnerable packages

## 🚨 Incident Response

### Health Check Endpoints
- **Application**: `GET /health/`
- **Database**: `GET /health/db/`
- **Cache**: `GET /health/cache/`
- **Celery**: `GET /health/celery/`

### Common Issues & Solutions

#### High Memory Usage
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Restart services if needed
sudo supervisorctl restart taruvi-web
sudo supervisorctl restart taruvi-celery
```

#### Database Connection Issues
```bash
# Check PostgreSQL connections
SELECT count(*) FROM pg_stat_activity;

# Kill idle connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < NOW() - INTERVAL '1 hour';
```

#### Celery Worker Issues
```bash
# Check Celery status
celery -A taruvi_project inspect active
celery -A taruvi_project inspect stats

# Restart workers
sudo supervisorctl restart taruvi-celery
```

## 📝 Maintenance Tasks

### Regular Maintenance
```bash
# Weekly maintenance script
#!/bin/bash

# Clean up old log files
find /var/log/taruvi -name "*.log.*" -mtime +7 -delete

# Clean up old Celery results
python manage.py shell -c "
from django_celery_results.models import TaskResult
from django.utils import timezone
from datetime import timedelta
TaskResult.objects.filter(date_created__lt=timezone.now() - timedelta(days=30)).delete()
"

# Update dependencies (staging first)
pip list --outdated

# Database maintenance
python manage.py clearsessions
```

### Scaling Considerations
- **Horizontal scaling**: Add more web workers/servers
- **Database scaling**: Read replicas, connection pooling
- **Cache scaling**: Redis cluster with sharding
- **Storage scaling**: S3 with CloudFront for global distribution

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] All tests pass in staging environment
- [ ] Database migrations tested
- [ ] Static files uploaded to CDN
- [ ] Environment variables updated
- [ ] SSL certificates valid
- [ ] Monitoring configured

### During Deployment
- [ ] Take database backup
- [ ] Enable maintenance mode (optional)
- [ ] Deploy application code
- [ ] Run database migrations
- [ ] Update static files
- [ ] Restart application services
- [ ] Verify health checks
- [ ] Disable maintenance mode

### Post-Deployment
- [ ] Monitor application logs
- [ ] Check error rates in Sentry
- [ ] Verify database connections
- [ ] Test critical user flows
- [ ] Update monitoring dashboards

## 📞 Support & Monitoring

### Alerting Rules
- HTTP 5xx error rate > 1%
- Database connection failures
- Celery queue length > 1000
- Memory usage > 80%
- Disk space < 20%
- SSL certificate expiry < 30 days

### Log Monitoring
```bash
# Key log patterns to monitor
tail -f /var/log/taruvi/*.log | grep -E "(ERROR|CRITICAL|Exception)"
```

---

**Production deployment requires careful planning and testing. Always test in staging first!**
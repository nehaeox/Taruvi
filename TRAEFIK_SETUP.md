# Traefik Multi-Tenant Development Setup

This guide helps you set up Traefik as a reverse proxy for local multi-tenant development with django-tenants, allowing you to access tenant subdomains like `tenant1.localhost` without modifying `/etc/hosts`.

## Quick Start

### 1. Run the Setup Script
```bash
./traefik-setup.sh
```
The script will ask you to choose between:
- **Option 1**: Use containerized PostgreSQL (good for new setups)
- **Option 2**: Use your existing external database

If you choose Option 2, make sure to update your `.env` file with the correct database credentials.

### 2. Create Demo Tenants
```bash
# Create a demo tenant
docker-compose -f docker-compose.yml exec web python manage.py create_demo_tenant demo1

# Create another tenant with custom name
docker-compose -f docker-compose.yml exec web python manage.py create_demo_tenant mycompany --name "My Company"
```

### 3. Access Your Application
- **Main App**: http://localhost
- **Admin**: http://localhost/admin/
- **API Docs**: http://localhost/api/docs/
- **Traefik Dashboard**: http://localhost:8080
- **Demo Tenant**: http://demo1.localhost
- **Company Tenant**: http://mycompany.localhost

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Browser       │    │   Traefik       │    │   Django        │
│                 │    │   (Port 80)     │    │   (Port 8000)   │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ localhost       │───▶│ Host: localhost │───▶│ Public Schema   │
│ tenant1.localhost│───▶│ Host: *.localhost│───▶│ Tenant Schema  │
│ tenant2.localhost│───▶│ Host: *.localhost│───▶│ Tenant Schema  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## How It Works

1. **Traefik** listens on port 80 and routes requests based on hostname
2. **Docker Labels** on the Django container tell Traefik how to route:
   - `localhost` → Public schema (platform admin)
   - `*.localhost` → Tenant schemas (individual tenants)
3. **Django-tenants** middleware determines which schema to use based on the domain
4. **No /etc/hosts** modification needed - `.localhost` domains resolve automatically

## Database Setup Options

### Option 1: Containerized Database (Recommended for new setups)
```bash
# Start with containerized PostgreSQL
./traefik-setup.sh  # Choose option 1
```
- PostgreSQL runs in Docker container
- Automatic database creation and setup
- Data persisted in Docker volume
- Easy to reset and clean up

### Option 2: External Database (Use existing database)
```bash
# Update .env file first
DB_HOST=localhost        # or your database host
DB_NAME=your_db_name
DB_USER=your_username  
DB_PASSWORD=your_password

# Then run setup
./traefik-setup.sh  # Choose option 2
```
- Use your existing PostgreSQL installation
- More control over database configuration
- Can share database with other projects
- Requires manual database creation

### Manual Database Commands
```bash
# Start only containerized database
docker-compose -f docker-compose.yml --profile db up -d db

# Start without database (external DB)
docker-compose -f docker-compose.yml up -d traefik web

# Start everything (including containerized DB)
docker-compose -f docker-compose.yml --profile db up -d
```

## Services

### Traefik (Port 80, 8080)
- **Purpose**: Reverse proxy and load balancer
- **Dashboard**: http://localhost:8080
- **Routes**: HTTP traffic to Django based on hostname

### PostgreSQL (Port 5432) - Optional
- **Purpose**: Database with tenant schemas
- **Schemas**: `public` (shared), `demo1`, `mycompany`, etc.
- **Note**: Only starts when using `--profile db` or setup script option 1

### Django (Port 8000)
- **Purpose**: Multi-tenant web application
- **Access**: Through Traefik on port 80

## Manual Tenant Creation

If you prefer creating tenants through the admin interface:

1. Go to http://localhost/admin/
2. Create a new **Client**:
   - Name: "My Company"
   - Schema name: "mycompany"
3. Create a new **Domain**:
   - Domain: "mycompany.localhost"
   - Tenant: Select the client you just created
   - Is primary: ✓
4. Access your tenant at http://mycompany.localhost

## Useful Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.yml logs -f

# Specific service
docker-compose -f docker-compose.yml logs -f web
docker-compose -f docker-compose.yml logs -f traefik
```

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.yml restart

# Restart specific service
docker-compose -f docker-compose.yml restart web
```

### Stop Everything
```bash
docker-compose -f docker-compose.yml down
```

### Database Operations
```bash
# Shared migrations
docker-compose -f docker-compose.yml exec web python manage.py migrate_schemas --shared

# Tenant migrations
docker-compose -f docker-compose.yml exec web python manage.py migrate_schemas --tenant

# List all tenants
docker-compose -f docker-compose.yml exec web python manage.py list_tenants
```

### Access Shell
```bash
# Django shell
docker-compose -f docker-compose.yml exec web python manage.py shell

# Container bash
docker-compose -f docker-compose.yml exec web bash
```

## Troubleshooting

### Domain Not Resolving
- Ensure Traefik is running: `docker ps`
- Check Traefik dashboard: http://localhost:8080
- Verify Docker labels in `docker-compose.traefik.yml`

### Django Not Loading
- Check container logs: `docker-compose -f docker-compose.traefik.yml logs web`
- Verify database connection
- Ensure migrations are run

### Traefik Dashboard Not Loading
- Check if port 8080 is available
- Verify Traefik container is running
- Check Traefik logs: `docker-compose -f docker-compose.traefik.yml logs traefik`

### Tenant Not Found
- Verify tenant exists in database
- Check domain configuration
- Ensure schema migrations are run for tenant

## Benefits Over /etc/hosts

✅ **No system file modification**  
✅ **Dynamic tenant creation**  
✅ **Easy team setup**  
✅ **Production-like environment**  
✅ **Automatic SSL termination support** (future)  
✅ **Load balancing capabilities** (future)  
✅ **Request routing and middleware**  

## Next Steps

- Add SSL/TLS certificates for HTTPS
- Configure additional middleware (rate limiting, auth)
- Set up monitoring and metrics
- Add health checks and service discovery
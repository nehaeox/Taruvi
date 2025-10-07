# Multi-Tenant Architecture Rules

## Schema-Based Multi-Tenancy
- This project uses schema-based multi-tenancy via `django-tenants`
- All tenant-specific models must be placed in `TENANT_APPS`, not `SHARED_APPS`
- Platform-wide infrastructure models belong in `SHARED_APPS`
- Never mix tenant and shared data access patterns in the same code block

## Tenant vs Shared App Classification
- **SHARED_APPS**: Platform infrastructure (django_tenants, admin, core tenant management, celery tasks)
- **TENANT_APPS**: Project-specific functionality (project users, business data, content specific to each client)
- When creating new apps, explicitly decide whether they belong in shared or tenant scope
- Authentication models exist in both contexts but serve different purposes (platform admins vs project users)

## Database Access Patterns
- Use `Client.objects` and `Domain.objects` only in shared schema context
- Project-specific data access assumes tenant context is already set by middleware
- Never perform raw SQL queries that access multiple schemas simultaneously
- Use `TenantMixin` for tenant models and `DomainMixin` for domain models

## Middleware Considerations
- `django_tenants.middleware.main.TenantMainMiddleware` must be the first middleware
- All custom middleware must be tenant-aware and handle both shared and tenant contexts
- Request processing must respect the current tenant context set by the tenant middleware

## URL Routing
- Tenant-specific URLs are automatically isolated by the tenant middleware
- Shared URLs (like admin) are accessible from the platform domain
- API endpoints must be designed to work within tenant context
- Health checks and platform utilities should use shared schema

## Data Isolation Requirements
- Each tenant must have complete data isolation at the database schema level
- No cross-tenant data access is allowed without explicit platform admin privileges
- File uploads and static assets must be organized by tenant when applicable
- Background tasks must specify tenant context when processing tenant-specific data
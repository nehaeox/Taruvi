# API Overview

Taruvi provides a comprehensive REST API built with Django REST Framework, featuring JWT authentication, comprehensive documentation, and tenant-aware endpoints.

## Base URLs

The API is accessible at different endpoints depending on the context:

```
# Platform API (shared resources)
https://api.yourdomain.com/api/

# Tenant-specific API  
https://tenant.yourdomain.com/api/

# Development
http://localhost:8000/api/                    # Platform API
http://tenant.127.0.0.1.nip.io:8000/api/     # Tenant API
```

## API Documentation

### Interactive Documentation

- **Swagger UI**: `/api/docs/` - Interactive API explorer
- **ReDoc**: `/api/redoc/` - Clean, responsive documentation
- **OpenAPI Schema**: `/api/schema/` - Machine-readable API specification

### Example URLs
```bash
# Production
https://api.yourdomain.com/api/docs/
https://tenant.yourdomain.com/api/docs/

# Development
http://localhost:8000/api/docs/
http://tenant.127.0.0.1.nip.io:8000/api/docs/
```

## Authentication

Taruvi uses **JWT (JSON Web Tokens)** for API authentication with support for token refresh and blacklisting.

### Obtaining Tokens

**Request**
```bash
POST /api/auth/jwt/token/
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "your-password"
}
```

**Response**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Using Access Tokens

Include the access token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     https://api.yourdomain.com/api/organizations/
```

### Token Refresh

Access tokens expire after 15 minutes. Use the refresh token to obtain a new access token:

```bash
POST /api/auth/jwt/token/refresh/
Content-Type: application/json

{
  "refresh": "YOUR_REFRESH_TOKEN"
}
```

### Token Blacklisting

Logout by blacklisting the refresh token:

```bash
POST /api/auth/jwt/token/blacklist/
Content-Type: application/json

{
  "refresh": "YOUR_REFRESH_TOKEN"
}
```

## API Endpoints

### Platform-Level Endpoints

These endpoints are available on the main domain and manage platform-wide resources:

#### Organizations
```bash
GET    /api/organizations/              # List organizations
POST   /api/organizations/              # Create organization
GET    /api/organizations/{id}/         # Get organization details
PUT    /api/organizations/{id}/         # Update organization
DELETE /api/organizations/{id}/         # Delete organization
```

#### Organization Members
```bash
GET    /api/organizations/{id}/members/           # List members
POST   /api/organizations/{id}/members/           # Add member
GET    /api/organizations/{id}/members/{user_id}/ # Get member details
PUT    /api/organizations/{id}/members/{user_id}/ # Update member
DELETE /api/organizations/{id}/members/{user_id}/ # Remove member
```

#### Sites (Tenants)
```bash
GET    /api/sites/                      # List sites
POST   /api/sites/                      # Create site
GET    /api/sites/{id}/                 # Get site details
PUT    /api/sites/{id}/                 # Update site
DELETE /api/sites/{id}/                 # Delete site
```

#### Invitations
```bash
GET    /api/invitations/                # List invitations
POST   /api/invitations/                # Send invitation
GET    /api/invitations/{id}/           # Get invitation details
POST   /api/invitations/{id}/accept/    # Accept invitation
POST   /api/invitations/{id}/decline/   # Decline invitation
```

### Tenant-Level Endpoints

These endpoints are available on tenant subdomains and operate within the tenant's isolated environment:

#### Users (Tenant-specific)
```bash
GET    /api/users/                      # List tenant users
POST   /api/users/                      # Create user
GET    /api/users/{id}/                 # Get user details
PUT    /api/users/{id}/                 # Update user
DELETE /api/users/{id}/                 # Delete user
```

#### Profile Management
```bash
GET    /api/profile/                    # Get current user profile
PUT    /api/profile/                    # Update profile
POST   /api/profile/change-password/    # Change password
```

## Request/Response Format

### Content Types

All API endpoints accept and return JSON data:
```
Content-Type: application/json
Accept: application/json
```

### Standard Response Format

**Success Response**
```json
{
  "id": 1,
  "name": "Example Organization",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**List Response**
```json
{
  "count": 25,
  "next": "https://api.example.com/api/organizations/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Organization 1",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Error Response**
```json
{
  "error": "Invalid request",
  "detail": "This field is required.",
  "code": "required"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200  | OK - Request successful |
| 201  | Created - Resource created successfully |
| 204  | No Content - Request successful, no content returned |
| 400  | Bad Request - Invalid request data |
| 401  | Unauthorized - Authentication required |
| 403  | Forbidden - Permission denied |
| 404  | Not Found - Resource not found |
| 429  | Too Many Requests - Rate limit exceeded |
| 500  | Internal Server Error - Server error |

## Pagination

List endpoints support pagination with configurable page sizes:

**Query Parameters**
```bash
GET /api/organizations/?page=2&page_size=20
```

**Response**
```json
{
  "count": 150,
  "next": "https://api.example.com/api/organizations/?page=3&page_size=20",
  "previous": "https://api.example.com/api/organizations/?page=1&page_size=20",
  "results": [...]
}
```

**Pagination Controls**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

## Filtering and Searching

Many endpoints support filtering and searching:

**Query Parameters**
```bash
# Filter by status
GET /api/organizations/?is_active=true

# Search by name
GET /api/organizations/?search=acme

# Multiple filters
GET /api/organizations/?is_active=true&created_at__gte=2024-01-01

# Ordering
GET /api/organizations/?ordering=-created_at
```

**Common Filter Fields**
- `is_active`: Boolean status filter
- `created_at__gte`: Date greater than or equal
- `created_at__lte`: Date less than or equal
- `search`: Text search across relevant fields
- `ordering`: Sort by field (prefix with `-` for descending)

## Rate Limiting

The API implements rate limiting to prevent abuse:

**Default Limits**
- **Authenticated Users**: 1000 requests per hour
- **Anonymous Users**: 100 requests per hour
- **Burst Protection**: 10 requests per minute

**Rate Limit Headers**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642608000
```

**Rate Limit Exceeded**
```json
{
  "error": "Rate limit exceeded",
  "detail": "Too many requests. Please try again later.",
  "retry_after": 3600
}
```

## Error Handling

The API uses consistent error formatting across all endpoints:

**Validation Errors**
```json
{
  "error": "Validation failed",
  "details": {
    "name": ["This field is required."],
    "email": ["Enter a valid email address."]
  }
}
```

**Permission Errors**
```json
{
  "error": "Permission denied",
  "detail": "You do not have permission to perform this action."
}
```

**Not Found Errors**
```json
{
  "error": "Not found",
  "detail": "Organization with id 999 does not exist."
}
```

## CORS Configuration

The API supports Cross-Origin Resource Sharing (CORS) for web applications:

**Allowed Origins**
```python
# Development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Production - configure as needed
CORS_ALLOWED_ORIGINS = [
    "https://app.yourdomain.com",
]
```

## API Versioning

Currently, Taruvi uses URL-based versioning:

```bash
# Current version (v1)
GET /api/organizations/

# Future versions
GET /api/v2/organizations/
```

Version changes will be documented and backward compatibility maintained where possible.

## Examples

### Complete Authentication Flow

```bash
# 1. Obtain tokens
curl -X POST https://api.yourdomain.com/api/auth/jwt/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@example.com", "password": "password"}'

# Response: {"access": "...", "refresh": "..."}

# 2. Use access token
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     https://api.yourdomain.com/api/organizations/

# 3. Refresh when expired
curl -X POST https://api.yourdomain.com/api/auth/jwt/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "YOUR_REFRESH_TOKEN"}'
```

### Creating an Organization

```bash
curl -X POST https://api.yourdomain.com/api/organizations/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "description": "Leading provider of innovative solutions",
    "subscription_plan": "enterprise"
  }'
```

### Tenant-Specific Requests

```bash
# Switch to tenant subdomain for tenant-specific operations
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     https://acme.yourdomain.com/api/users/

# Or use development setup
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     http://acme.127.0.0.1.nip.io:8000/api/users/
```

Ready to start using the API? Check out the [interactive documentation](http://localhost:8000/api/docs/) or explore specific endpoint details in our API reference.
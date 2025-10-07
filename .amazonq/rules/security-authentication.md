# Security and Authentication Rules

## JWT Authentication Standards
- Use `rest_framework_simplejwt` for all API authentication
- Access tokens must expire within 15 minutes maximum
- Refresh tokens must expire within 7 days maximum
- Always enable refresh token rotation (`ROTATE_REFRESH_TOKENS = True`)
- Blacklist rotated refresh tokens (`BLACKLIST_AFTER_ROTATION = True`)
- Never store JWT tokens in localStorage - use secure HTTP-only cookies when possible

## API Security Requirements
- All API endpoints must require authentication unless explicitly designed for public access
- Implement rate limiting on all API endpoints using the provided decorators (`@api_rate_limit()`, `@burst_rate_limit()`)
- Authentication endpoints must have additional rate limiting (`@auth_rate_limit()`)
- Use appropriate DRF permission classes (`IsAuthenticated`, `IsAdminUser`, etc.)

## Security Headers and Middleware
- All responses must include security headers (XSS protection, content type sniffing, frame options)
- HTTPS must be enforced in production (`SECURE_SSL_REDIRECT = True`)
- Enable HSTS headers with at least 1 year expiry (`SECURE_HSTS_SECONDS = 31536000`)
- Set secure cookie flags in production (`SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`)
- Use `SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'`

## Password and User Management
- Never log or store plaintext passwords
- Use Django's built-in password validation
- Implement proper password reset flows with token expiration
- User creation must include proper validation and sanitization
- Multi-factor authentication should be supported for admin accounts

## Input Validation and Sanitization
- All user inputs must be validated using Django forms or DRF serializers
- Never construct raw SQL queries with user input
- Use Django's built-in CSRF protection
- Validate file uploads for type, size, and content
- Sanitize all data before logging to prevent log injection

## AWS Security Requirements
- S3 buckets must have encryption enabled
- S3 buckets must block public access unless specifically required
- S3 bucket policies must enforce SSL/TLS for all requests
- SQS queues must use encryption in transit and at rest
- IAM roles must follow principle of least privilege
- Never commit AWS credentials to code - use environment variables or IAM roles

## Error Handling and Logging
- Never expose sensitive information in error messages or logs
- Log all authentication failures and security-related events
- Use correlation IDs for request tracing without exposing sensitive data
- Implement proper exception handling to prevent information disclosure
- Monitor and alert on suspicious security events
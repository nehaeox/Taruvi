from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from django.conf import settings
from functools import wraps
import logging

logger = logging.getLogger('security')


def conditional_ratelimit(group=None, key=None, rate=None, method=None, block=True):
    """
    Conditional rate limiting decorator that respects the RATE_LIMIT_ENABLE setting
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Check if rate limiting is enabled
            if not getattr(settings, 'RATE_LIMIT_ENABLE', True):
                return func(request, *args, **kwargs)
            
            # Apply rate limiting
            rate_limit_decorator = ratelimit(
                group=group,
                key=key or 'ip',
                rate=rate or f"{settings.API_RATE_LIMIT_PER_MINUTE}/m",
                method=method or ['GET', 'POST'],
                block=block
            )
            
            return rate_limit_decorator(func)(request, *args, **kwargs)
        
        return wrapper
    return decorator


def api_rate_limit(rate=None, key=None, group=None):
    """
    Standard API rate limiting decorator
    """
    return conditional_ratelimit(
        group=group or 'api',
        key=key or 'user_or_ip',
        rate=rate or f"{getattr(settings, 'API_RATE_LIMIT_PER_MINUTE', 100)}/m",
        method=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
        block=True
    )


def burst_rate_limit(rate=None, key=None, group=None):
    """
    Burst rate limiting decorator for protecting against rapid requests
    """
    return conditional_ratelimit(
        group=group or 'burst',
        key=key or 'user_or_ip', 
        rate=rate or f"{getattr(settings, 'API_RATE_LIMIT_BURST', 10)}/s",
        method=['POST', 'PUT', 'DELETE', 'PATCH'],
        block=True
    )


def auth_rate_limit(rate='5/m', key='ip', group='auth'):
    """
    Strict rate limiting for authentication endpoints
    """
    return conditional_ratelimit(
        group=group,
        key=key,
        rate=rate,
        method=['POST'],
        block=True
    )


def conditional_cache(timeout=None, key_prefix=None, vary=None):
    """
    Conditional caching decorator that respects cache settings
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Check if caching is enabled
            cache_enabled = getattr(settings, 'API_CACHE_ENABLED', False)
            if not cache_enabled:
                return func(request, *args, **kwargs)
            
            # Apply caching
            cache_timeout = timeout or getattr(settings, 'API_CACHE_TTL', 300)
            cache_decorator = cache_page(
                cache_timeout,
                key_prefix=key_prefix,
                vary=vary
            )
            
            return cache_decorator(func)(request, *args, **kwargs)
        
        return wrapper
    return decorator


def log_api_access(action=None):
    """
    Decorator to log API access for audit purposes
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Log API access
            logger.info(
                f"API Access: {action or func.__name__}",
                extra={
                    'correlation_id': getattr(request, 'correlation_id', None),
                    'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
                    'method': request.method,
                    'path': request.get_full_path(),
                    'remote_addr': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'action': action or func.__name__,
                    'event_type': 'api_access'
                }
            )
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_api_key(header_name='X-API-Key'):
    """
    Decorator to require API key authentication
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            api_key = request.META.get(f'HTTP_{header_name.upper().replace("-", "_")}')
            
            if not api_key:
                logger.warning(
                    "API key missing",
                    extra={
                        'correlation_id': getattr(request, 'correlation_id', None),
                        'path': request.get_full_path(),
                        'remote_addr': request.META.get('REMOTE_ADDR'),
                        'event_type': 'auth_failure'
                    }
                )
                return JsonResponse(
                    {'error': 'API key required'},
                    status=401
                )
            
            # Validate API key (implement your validation logic)
            valid_api_keys = getattr(settings, 'VALID_API_KEYS', [])
            if valid_api_keys and api_key not in valid_api_keys:
                logger.warning(
                    "Invalid API key",
                    extra={
                        'correlation_id': getattr(request, 'correlation_id', None),
                        'path': request.get_full_path(),
                        'remote_addr': request.META.get('REMOTE_ADDR'),
                        'api_key_prefix': api_key[:8] + '...' if len(api_key) > 8 else api_key,
                        'event_type': 'auth_failure'
                    }
                )
                return JsonResponse(
                    {'error': 'Invalid API key'},
                    status=401
                )
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def tenant_required(func):
    """
    Decorator to ensure request is made in tenant context
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        from django_tenants.utils import get_tenant
        
        try:
            tenant = get_tenant(request)
            if not tenant or tenant.schema_name == getattr(settings, 'PUBLIC_SCHEMA_NAME', 'public'):
                return JsonResponse(
                    {'error': 'Tenant context required'},
                    status=400
                )
        except Exception as e:
            logger.error(
                f"Tenant context error: {e}",
                extra={
                    'correlation_id': getattr(request, 'correlation_id', None),
                    'event_type': 'tenant_error'
                }
            )
            return JsonResponse(
                {'error': 'Invalid tenant context'},
                status=400
            )
        
        return func(request, *args, **kwargs)
    
    return wrapper
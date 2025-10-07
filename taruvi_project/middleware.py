import uuid
import logging
import threading
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse

# Thread local storage for correlation ID
_thread_locals = threading.local()

def get_correlation_id():
    """Get the current request correlation ID"""
    return getattr(_thread_locals, 'correlation_id', None)

def set_correlation_id(correlation_id):
    """Set the current request correlation ID"""
    _thread_locals.correlation_id = correlation_id

class CorrelationIdMiddleware(MiddlewareMixin):
    """
    Middleware to add correlation ID to all requests for tracing
    """
    def process_request(self, request):
        # Get correlation ID from header or generate new one
        correlation_id = request.META.get('HTTP_X_CORRELATION_ID', str(uuid.uuid4()))
        
        # Store in thread local
        set_correlation_id(correlation_id)
        
        # Add to request object
        request.correlation_id = correlation_id
        
        return None
    
    def process_response(self, request, response):
        # Add correlation ID to response headers
        correlation_id = getattr(request, 'correlation_id', None)
        if correlation_id:
            response['X-Correlation-ID'] = correlation_id
        
        return response

class SecurityLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log security-related events
    """
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.security_logger = logging.getLogger('security')
        
    def process_request(self, request):
        # Log potential security issues
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        remote_addr = request.META.get('REMOTE_ADDR', '')
        
        # Check for suspicious patterns
        suspicious_patterns = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'burp', 'scanner',
            '<script', 'javascript:', 'eval(', 'alert(', 'onload=',
            '../', '.env', 'wp-admin', 'phpmyadmin'
        ]
        
        is_suspicious = any(pattern in user_agent.lower() or 
                          pattern in request.get_full_path().lower() 
                          for pattern in suspicious_patterns)
        
        if is_suspicious:
            self.security_logger.warning(
                "Suspicious request detected",
                extra={
                    'correlation_id': getattr(request, 'correlation_id', None),
                    'path': request.get_full_path(),
                    'method': request.method,
                    'user_agent': user_agent,
                    'remote_addr': remote_addr,
                    'x_forwarded_for': x_forwarded_for,
                    'event_type': 'suspicious_request'
                }
            )
        
        return None

class APILoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests and responses
    """
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.api_logger = logging.getLogger('api')
        
    def process_request(self, request):
        # Only log API requests (paths starting with /api/)
        if request.path.startswith('/api/'):
            import time
            request._start_time = time.time()
            
            self.api_logger.info(
                f"API Request: {request.method} {request.get_full_path()}",
                extra={
                    'correlation_id': getattr(request, 'correlation_id', None),
                    'method': request.method,
                    'path': request.get_full_path(),
                    'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'remote_addr': request.META.get('REMOTE_ADDR', ''),
                    'event_type': 'api_request'
                }
            )
        
        return None
    
    def process_response(self, request, response):
        # Only log API responses
        if request.path.startswith('/api/') and hasattr(request, '_start_time'):
            import time
            duration = time.time() - request._start_time
            
            self.api_logger.info(
                f"API Response: {request.method} {request.get_full_path()} - {response.status_code}",
                extra={
                    'correlation_id': getattr(request, 'correlation_id', None),
                    'method': request.method,
                    'path': request.get_full_path(),
                    'status_code': response.status_code,
                    'duration_ms': round(duration * 1000, 2),
                    'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
                    'event_type': 'api_response'
                }
            )
        
        return response

class CustomLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically adds correlation ID to log records
    """
    def process(self, msg, kwargs):
        correlation_id = get_correlation_id()
        if correlation_id:
            # Add correlation ID to log record
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra']['correlation_id'] = correlation_id
        
        return msg, kwargs

# Helper function to get a logger with correlation ID support
def get_logger(name):
    """Get a logger that automatically includes correlation ID"""
    logger = logging.getLogger(name)
    return CustomLoggerAdapter(logger, {})
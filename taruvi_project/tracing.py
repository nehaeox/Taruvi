import os
from django.conf import settings

def configure_opentelemetry():
    """Configure OpenTelemetry with automatic instrumentation"""
    
    # Check if OpenTelemetry is enabled
    if not getattr(settings, 'OTEL_ENABLED', True):
        return
    
    # Let OpenTelemetry auto-instrument everything
    from opentelemetry.instrumentation.auto_instrumentation import sitecustomize

def get_tracer(name: str = None):
    """Get a tracer instance"""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name or __name__)
    except ImportError:
        # Return a no-op tracer if OpenTelemetry is not available
        class NoOpTracer:
            def start_as_current_span(self, name):
                return NoOpSpan()
        return NoOpTracer()

class NoOpSpan:
    """No-op span for when tracing is disabled"""
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def set_attribute(self, key, value):
        pass
    
    def set_attributes(self, attributes):
        pass
    
    def record_exception(self, exception):
        pass

def trace_function(name: str = None, attributes: dict = None):
    """Decorator to trace function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not getattr(settings, 'OTEL_ENABLED', True):
                return func(*args, **kwargs)
            
            tracer = get_tracer(__name__)
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    span.set_attributes(attributes)
                
                # Add function arguments as attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("function.result_type", type(result).__name__)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    from opentelemetry.trace import StatusCode
                    span.set_status(StatusCode.ERROR, str(e))
                    raise
        
        return wrapper
    return decorator
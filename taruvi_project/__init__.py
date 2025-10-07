# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

# Configure OpenTelemetry
try:
    from .tracing import configure_opentelemetry
    configure_opentelemetry()
except Exception as e:
    # Don't fail startup if tracing configuration fails
    import logging
    logging.getLogger(__name__).warning(f"Failed to configure OpenTelemetry: {e}")

__all__ = ('celery_app',)
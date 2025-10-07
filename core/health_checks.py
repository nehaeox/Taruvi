from django.core.cache import cache
from django.db import connection
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import HealthCheckException
from celery import current_app as celery_app
import redis
import requests
from django.conf import settings


class CeleryHealthCheck(BaseHealthCheckBackend):
    """Custom health check for Celery workers"""
    
    critical_service = True
    
    def check_status(self):
        try:
            # Check if Celery workers are available
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            
            if not stats:
                self.add_error(HealthCheckException("No Celery workers available"))
                return
            
            # Check if workers are responsive
            active = inspect.active()
            if active is None:
                self.add_error(HealthCheckException("Celery workers not responding"))
                return
                
        except Exception as e:
            self.add_error(HealthCheckException(f"Celery health check failed: {str(e)}"))

    def identifier(self):
        return self.__class__.__name__


class RedisHealthCheck(BaseHealthCheckBackend):
    """Custom health check for Redis"""
    
    critical_service = True
    
    def check_status(self):
        try:
            # Test cache connection
            cache.set('health_check', 'ok', 30)
            result = cache.get('health_check')
            
            if result != 'ok':
                self.add_error(HealthCheckException("Cache read/write test failed"))
                
        except Exception as e:
            self.add_error(HealthCheckException(f"Redis health check failed: {str(e)}"))

    def identifier(self):
        return self.__class__.__name__


class DatabaseHealthCheck(BaseHealthCheckBackend):
    """Custom database health check with additional checks"""
    
    critical_service = True
    
    def check_status(self):
        try:
            # Test basic connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                
            # Check if we can access tenant schema
            from django_tenants.utils import tenant_context, get_public_schema_name
            from core.models import Client
            
            # Check public schema access
            public_schema = get_public_schema_name()
            if Client.objects.filter(schema_name=public_schema).exists():
                # Test tenant access if we have tenants
                pass
                
        except Exception as e:
            self.add_error(HealthCheckException(f"Database health check failed: {str(e)}"))

    def identifier(self):
        return self.__class__.__name__


class ExternalServiceHealthCheck(BaseHealthCheckBackend):
    """Health check for external services"""
    
    critical_service = False  # Not critical for application startup
    
    def check_status(self):
        try:
            # Check if configured external services are accessible
            external_services = getattr(settings, 'EXTERNAL_HEALTH_CHECKS', [])
            
            for service in external_services:
                url = service.get('url')
                timeout = service.get('timeout', 5)
                name = service.get('name', url)
                
                try:
                    response = requests.get(url, timeout=timeout)
                    if response.status_code != 200:
                        self.add_error(
                            HealthCheckException(f"External service {name} returned {response.status_code}")
                        )
                except requests.exceptions.RequestException as e:
                    self.add_error(
                        HealthCheckException(f"External service {name} unreachable: {str(e)}")
                    )
                    
        except Exception as e:
            self.add_error(HealthCheckException(f"External service health check failed: {str(e)}"))

    def identifier(self):
        return self.__class__.__name__
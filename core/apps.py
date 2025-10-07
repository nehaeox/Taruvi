from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    
    def ready(self):
        # Import signals if needed (currently disabled for direct admin approach)
        # from . import signals
        pass

from django.db import models
from core.models import BaseModel


class Function(BaseModel):
    """
    Test model for functions subapp
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    code = models.TextField(help_text="Function code or logic")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Function"
        verbose_name_plural = "Functions"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

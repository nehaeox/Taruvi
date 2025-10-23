from django.contrib import admin
from core.admin import BaseModelAdmin
from .models import Function


@admin.register(Function)
class FunctionAdmin(BaseModelAdmin):
    list_display = ('name', 'is_active', 'assigned_to', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'code')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Function Information', {
            'fields': ('name', 'description', 'code', 'is_active')
        }),
        ('Assignment', {
            'fields': ('assigned_to',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

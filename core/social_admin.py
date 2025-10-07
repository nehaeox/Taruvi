"""
Custom admin interfaces for tenant-scoped social authentication management.
"""

from django.contrib import admin
from django.contrib import messages
from django.forms import ModelForm, ValidationError
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.admin import SocialAppAdmin as BaseSocialAppAdmin
from django_tenants.utils import get_tenant_model, get_public_schema_name
from django.db import connection


class TenantSocialAppForm(ModelForm):
    """Custom form for SocialApp that validates tenant-specific configurations"""
    
    class Meta:
        model = SocialApp
        fields = '__all__'
    
    def clean_name(self):
        """Ensure social app names are unique within tenant scope"""
        name = self.cleaned_data['name']
        tenant = getattr(connection, 'tenant', None)
        
        if tenant and hasattr(tenant, 'schema_name'):
            # Add tenant prefix to ensure uniqueness across tenants
            if not name.startswith(f"{tenant.schema_name}_"):
                return f"{tenant.schema_name}_{name}"
        
        return name
    
    def clean(self):
        """Additional validation for tenant-specific social apps"""
        cleaned_data = super().clean()
        
        # Ensure we're not in public schema when creating tenant-specific apps
        if connection.schema_name == get_public_schema_name():
            raise ValidationError(
                "Tenant-specific social apps cannot be created in the public schema. "
                "Please switch to a specific tenant domain to configure authentication."
            )
        
        return cleaned_data


class TenantSocialAppAdmin(BaseSocialAppAdmin):
    """Custom admin for SocialApp that provides tenant-scoped management"""
    
    form = TenantSocialAppForm




    list_display = ('name', 'provider', 'client_id_truncated', 'sites_list', 'created_for_tenant')
    list_filter = ('provider',)
    search_fields = ('name', 'provider', 'client_id')
    
    fieldsets = (
        (None, {
            'fields': ('provider', 'name', 'client_id', 'secret')
        }),
        ('Configuration', {
            'fields': ('key', 'settings'),
            'classes': ('collapse',)
        }),
        ('Sites', {
            'fields': ('sites',),
            'description': 'Select the sites where this social app should be available.'
        }),
    )
    
    def get_queryset(self, request):
        """Filter social apps to show only tenant-relevant ones"""
        qs = super().get_queryset(request)
        
        # If we're in a tenant schema, show apps that belong to this tenant
        if hasattr(connection, 'tenant') and connection.schema_name != get_public_schema_name():
            tenant_prefix = f"{connection.schema_name}_"
            qs = qs.filter(name__startswith=tenant_prefix)
        
        return qs
    
    def client_id_truncated(self, obj):
        """Show truncated client ID for security"""
        if obj.client_id:
            return f"{obj.client_id[:8]}..."
        return "-"
    client_id_truncated.short_description = "Client ID"
    
    def sites_list(self, obj):
        """Show associated sites"""
        sites = obj.sites.all()
        if sites:
            return ", ".join([site.domain for site in sites[:3]])
        return "No sites"
    sites_list.short_description = "Sites"
    
    def created_for_tenant(self, obj):
        """Show which tenant this was created for"""
        if obj.name and "_" in obj.name:
            tenant_prefix = obj.name.split("_")[0]
            return tenant_prefix
        return "Public"
    created_for_tenant.short_description = "Tenant"
    
    def save_model(self, request, obj, form, change):
        """Custom save logic for tenant-aware social apps"""
        
        if not change:  # New object
            # Auto-assign to current site if we're in a tenant context
            if hasattr(connection, 'tenant') and connection.schema_name != get_public_schema_name():
                messages.info(
                    request, 
                    f"Social app '{obj.name}' created for tenant: {connection.schema_name}"
                )
        
        super().save_model(request, obj, form, change)
        
        # Auto-assign to current tenant's sites
        if hasattr(connection, 'tenant') and connection.schema_name != get_public_schema_name():
            from django.contrib.sites.models import Site
            try:
                # Try to find a site that matches the current tenant
                current_site = Site.objects.get_current()
                obj.sites.add(current_site)
            except:
                # If no current site found, add to all sites (fallback)
                pass
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on context"""
        form = super().get_form(request, obj, **kwargs)
        
        # Add help text for tenant context
        if hasattr(connection, 'tenant') and connection.schema_name != get_public_schema_name():
            help_texts = form.base_fields.get('name', None)
            if help_texts:
                help_texts.help_text = (
                    f"Social app for tenant: {connection.schema_name}. "
                    f"Name will be automatically prefixed for tenant isolation."
                )
        
        return form
    
    def changelist_view(self, request, extra_context=None):
        """Add tenant context to changelist"""
        extra_context = extra_context or {}
        
        if hasattr(connection, 'tenant') and connection.schema_name != get_public_schema_name():
            extra_context['tenant_name'] = connection.tenant.name
            extra_context['tenant_schema'] = connection.schema_name
        else:
            extra_context['is_public_schema'] = True
            
        return super().changelist_view(request, extra_context)


# Unregister the original SocialApp admin and register our custom one
admin.site.unregister(SocialApp)
admin.site.register(SocialApp, TenantSocialAppAdmin)
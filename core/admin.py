from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import get_object_or_404
from guardian.admin import GuardedModelAdmin
from guardian.shortcuts import assign_perm, remove_perm, get_users_with_perms
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Site, Domain, Organization, OrganizationMember, 
    OrganizationSite, OrganizationInvitation
)

# Import custom social admin to register tenant-aware SocialApp admin
try:
    from . import social_admin
except ImportError:
    pass


class BaseModelAdmin(admin.ModelAdmin):
    """
    Mixin for admin classes that handle BaseModel subclasses.
    
    Automatically populates created_by and modified_by fields,
    and provides common readonly fields and optimization.
    """
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'modified_by')
    
    def get_queryset(self, request):
        """Optimize queries by selecting related user fields"""
        qs = super().get_queryset(request)
        # Only select related fields if they exist in the model
        select_related_fields = []
        if hasattr(self.model, 'created_by'):
            select_related_fields.append('created_by')
        if hasattr(self.model, 'modified_by'):
            select_related_fields.append('modified_by')
        if hasattr(self.model, 'assigned_to'):
            select_related_fields.append('assigned_to')
        
        if select_related_fields:
            qs = qs.select_related(*select_related_fields)
        return qs
    
    def save_model(self, request, obj, form, change):
        """Auto-populate user tracking fields"""
        if hasattr(obj, 'created_by') and not change:  # Creating new object
            obj.created_by = request.user
        if hasattr(obj, 'modified_by'):
            obj.modified_by = request.user
        super().save_model(request, obj, form, change)


class DomainInline(admin.TabularInline):
    """Inline editor for domains within Site admin"""
    model = Domain
    extra = 1
    fields = ('domain', 'is_primary')
    verbose_name = "Domain"
    verbose_name_plural = "Domains"
    
    def get_extra(self, request, obj=None, **kwargs):
        """Only show extra field for new sites"""
        if obj:
            return 0
        return 1


@admin.register(Site)
class SiteAdmin(GuardedModelAdmin, TenantAdminMixin, SimpleHistoryAdmin):
    list_display = ('name', 'schema_name', 'primary_domain', 'created_on', 'is_active', 'user_count')
    list_filter = ('created_on', 'is_active')
    search_fields = ('name', 'schema_name', 'domains__domain')
    readonly_fields = ('created_on', 'user_count', 'primary_domain')
    inlines = [DomainInline]
    actions = ['manage_site_permissions']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'schema_name'),
            'description': 'The database schema will be created automatically when you save.'
        }),
        ('Additional Info', {
            'fields': ('description',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Domain Information', {
            'fields': ('primary_domain',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_on', 'user_count'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).prefetch_related('organization_sites', 'domains')
    
    def primary_domain(self, obj):
        """Display the primary domain for this site"""
        try:
            primary = obj.domains.filter(is_primary=True).first()
            if primary:
                return format_html('<a href="{}" target="_blank">{}</a>', 
                    f"http://{primary.domain}:8000",
                    primary.domain
                )
            return format_html('<span style="color: orange;">⚠ No primary domain set</span>')
        except:
            return "Unknown"
    primary_domain.short_description = 'Primary Domain'
    
    def user_count(self, obj):
        """Display count of users with access to this site"""
        from guardian.shortcuts import get_users_with_perms
        users = get_users_with_perms(obj, only_with_perms_in=['access_site'])
        return users.count()
    user_count.short_description = 'Users with Access'
    
    def save_model(self, request, obj, form, change):
        """Save the site and handle schema creation"""
        # Let django-tenants handle schema creation with auto_create_schema=True
        super().save_model(request, obj, form, change)
        
        if not change:  # Only for new sites
            # Run migrations for the newly created schema
            try:
                from django.core.management import call_command
                call_command('migrate_schemas', schema_name=obj.schema_name, verbosity=0)
                
                messages.success(
                    request,
                    f'Site "{obj.name}" created successfully with schema "{obj.schema_name}" and migrations applied!'
                )
            except Exception as e:
                messages.warning(
                    request,
                    f'Site "{obj.name}" created with schema "{obj.schema_name}" but migration failed: {e}. '
                    f'Please run: python manage.py migrate_schemas --schema={obj.schema_name}'
                )


# Domain Admin (unregistered - managed via Site inline)
class DomainAdmin(SimpleHistoryAdmin):
    """Standalone Domain admin (available but not registered by default)"""
    list_display = ('domain', 'tenant', 'is_primary')
    list_filter = ('is_primary', 'tenant')
    search_fields = ('domain',)
    
    fieldsets = (
        ('Domain Information', {
            'fields': ('domain', 'tenant', 'is_primary'),
            'description': 'Note: Domains are typically managed through Site admin with inline editing.'
        }),
    )

# Uncomment below line if you need standalone Domain management
# admin.site.register(Domain, DomainAdmin)


# Organization Admin Classes

class OrganizationMemberInline(admin.TabularInline):
    """Inline for Organization Members"""
    model = OrganizationMember
    fields = ('user', 'role', 'title', 'department', 'is_active', 'joined_at')
    readonly_fields = ('joined_at',)
    extra = 0
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


class OrganizationSiteInline(admin.TabularInline):
    """Inline for Organization Sites"""
    model = OrganizationSite
    fields = ('site', 'is_primary', 'site_role', 'is_active', 'created_at')
    readonly_fields = ('created_at',)
    extra = 0
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('site')


class OrganizationInvitationInline(admin.TabularInline):
    """Inline for Organization Invitations"""
    model = OrganizationInvitation
    fields = ('email', 'role', 'is_accepted', 'expires_at', 'invited_by')
    readonly_fields = ('invited_by',)
    extra = 0
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            is_accepted=False, 
            expires_at__gt=timezone.now()
        ).select_related('invited_by')


@admin.register(Organization)
class OrganizationAdmin(GuardedModelAdmin, BaseModelAdmin, SimpleHistoryAdmin):
    """Admin for Organization with Guardian integration"""
    list_display = (
        'name', 'slug', 'subscription_plan', 'is_verified', 
        'member_count', 'owner_count', 'site_count', 'is_active', 'created_at'
    )
    list_filter = (
        'subscription_plan', 'is_verified', 'is_active', 
        'created_at', 'verified_at'
    )
    search_fields = ('name', 'slug', 'email', 'website')
    readonly_fields = (
        'slug', 'verified_at', 'member_count', 'owner_count', 'site_count',
        'created_at', 'updated_at', 'created_by', 'modified_by'
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'is_active'),
            'description': 'Organization identity and status'
        }),
        ('Contact Information', {
            'fields': ('email', 'website', 'phone', 'address'),
            'classes': ('collapse',)
        }),
        ('Subscription & Limits', {
            'fields': (
                'subscription_plan', 'max_sites', 'max_members',
                'member_count', 'site_count'
            ),
            'description': 'Subscription plan and usage limits'
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_at'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('owner_count',),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at', 'created_by', 'modified_by'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OrganizationMemberInline, OrganizationSiteInline, OrganizationInvitationInline]
    
    actions = ['verify_organizations', 'make_owners_of_organizations']
    
    def save_formset(self, request, form, formset, change):
        """Auto-populate invited_by field for new invitations"""
        instances = formset.save(commit=False)
        
        for instance in instances:
            # Auto-populate invited_by for new OrganizationInvitation instances
            if isinstance(instance, OrganizationInvitation):
                if not instance.pk and not instance.invited_by_id:  # New invitation
                    instance.invited_by = request.user
            
            instance.save()
        
        formset.save_m2m()
        super().save_formset(request, form, formset, change)
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            'members', 'organization_sites', 'invitations'
        ).select_related('created_by', 'modified_by')
    
    def member_count(self, obj):
        """Display member count"""
        return obj.get_member_count()
    member_count.short_description = 'Members'
    
    def owner_count(self, obj):
        """Display owner count"""
        return obj.get_owner_count()
    owner_count.short_description = 'Owners'
    
    def site_count(self, obj):
        """Display site count"""
        return obj.get_site_count()
    site_count.short_description = 'Sites'
    
    def verify_organizations(self, request, queryset):
        """Bulk action to verify organizations"""
        updated = queryset.filter(is_verified=False).update(
            is_verified=True,
            verified_at=timezone.now()
        )
        
        self.message_user(
            request,
            f'Successfully verified {updated} organization(s).',
            messages.SUCCESS
        )
    verify_organizations.short_description = "Verify selected organizations"
    
    def make_owners_of_organizations(self, request, queryset):
        """Bulk action to make current user owner of selected organizations"""
        from guardian.shortcuts import assign_perm
        
        for org in queryset:
            # Create organization member if doesn't exist
            member, created = OrganizationMember.objects.get_or_create(
                organization=org,
                user=request.user,
                defaults={
                    'role': 'owner',
                    'is_active': True,
                    'created_by': request.user,
                }
            )
            
            # Update to owner if exists
            if not created and member.role != 'owner':
                member.role = 'owner'
                member.is_active = True
                member.save()
            
            # Assign permissions
            assign_perm('view_organization', request.user, org)
            assign_perm('manage_organization', request.user, org)
            assign_perm('invite_members', request.user, org)
            assign_perm('manage_sites', request.user, org)
        
        count = queryset.count()
        self.message_user(
            request,
            f'You are now an owner of {count} organization(s).',
            messages.SUCCESS
        )
    make_owners_of_organizations.short_description = "Make me owner of selected organizations"


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(BaseModelAdmin, SimpleHistoryAdmin):
    """Admin for Organization Members"""
    list_display = (
        'user', 'organization', 'role', 'title', 'department',
        'is_active', 'joined_at', 'last_active'
    )
    list_filter = ('role', 'is_active', 'joined_at', 'last_active')
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'organization__name', 'title', 'department'
    )
    readonly_fields = ('joined_at', 'last_active', 'created_at', 'updated_at', 'created_by', 'modified_by')
    
    fieldsets = (
        ('Membership', {
            'fields': ('organization', 'user', 'role', 'is_active'),
            'description': 'Basic organization membership details'
        }),
        ('Profile Information', {
            'fields': ('title', 'department', 'phone'),
            'classes': ('collapse',)
        }),
        ('Activity', {
            'fields': ('joined_at', 'last_active'),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at', 'created_by', 'modified_by'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_owners', 'make_members', 'activate_members', 'deactivate_members', 'assign_to_all_org_sites']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'organization', 'created_by', 'modified_by'
        )
    
    def make_owners(self, request, queryset):
        """Bulk action to make selected members owners"""
        from guardian.shortcuts import assign_perm
        
        updated = 0
        for member in queryset.filter(role='member'):
            member.role = 'owner'
            member.save()
            
            # Assign owner permissions
            assign_perm('manage_organization', member.user, member.organization)
            assign_perm('invite_members', member.user, member.organization)
            assign_perm('manage_sites', member.user, member.organization)
            updated += 1
        
        self.message_user(
            request,
            f'Successfully made {updated} member(s) into owner(s).',
            messages.SUCCESS
        )
    make_owners.short_description = "Make selected members owners"
    
    def make_members(self, request, queryset):
        """Bulk action to make selected owners members"""
        from guardian.shortcuts import remove_perm
        
        updated = 0
        for member in queryset.filter(role='owner'):
            member.role = 'member'
            member.save()
            
            # Remove owner permissions (keep view permission)
            remove_perm('manage_organization', member.user, member.organization)
            remove_perm('invite_members', member.user, member.organization)
            remove_perm('manage_sites', member.user, member.organization)
            updated += 1
        
        self.message_user(
            request,
            f'Successfully demoted {updated} owner(s) to member(s).',
            messages.SUCCESS
        )
    make_members.short_description = "Make selected owners members"
    
    def activate_members(self, request, queryset):
        """Bulk action to activate members"""
        updated = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(
            request,
            f'Successfully activated {updated} member(s).',
            messages.SUCCESS
        )
    activate_members.short_description = "Activate selected members"
    
    def deactivate_members(self, request, queryset):
        """Bulk action to deactivate members"""
        updated = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(
            request,
            f'Successfully deactivated {updated} member(s).',
            messages.SUCCESS
        )
    deactivate_members.short_description = "Deactivate selected members"
    
    def assign_to_all_org_sites(self, request, queryset):
        """Bulk action to assign selected members to all their organization's sites"""
        from guardian.shortcuts import assign_perm
        
        total_assigned = 0
        for member in queryset.filter(is_active=True):
            org_sites = member.organization.organization_sites.filter(is_active=True)
            for org_site in org_sites:
                # Grant appropriate permissions based on role
                assign_perm('access_site', member.user, org_site.site)
                if member.role == 'owner':
                    assign_perm('admin_site', member.user, org_site.site)
                total_assigned += 1
        
        self.message_user(
            request,
            f'Assigned {total_assigned} site access permissions.',
            messages.SUCCESS
        )
    assign_to_all_org_sites.short_description = "Assign to all organization sites"


@admin.register(OrganizationSite)
class OrganizationSiteAdmin(BaseModelAdmin, SimpleHistoryAdmin):
    """Admin for Organization Sites"""
    list_display = (
        'organization', 'site', 'is_primary', 'site_role', 
        'is_active', 'user_count', 'created_at'
    )
    list_filter = ('is_primary', 'site_role', 'is_active', 'created_at')
    search_fields = ('organization__name', 'site__name', 'site__schema_name')
    readonly_fields = ('user_count', 'created_at', 'updated_at', 'created_by', 'modified_by')
    
    fieldsets = (
        ('Site Assignment', {
            'fields': ('organization', 'site', 'is_primary', 'site_role', 'is_active'),
            'description': 'Link organization to tenant site'
        }),
        ('Configuration', {
            'fields': ('site_settings',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('user_count',),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at', 'created_by', 'modified_by'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['grant_access_to_all_owners']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'organization', 'site', 'created_by', 'modified_by'
        )
    
    def user_count(self, obj):
        """Display count of users with access to this site"""
        from guardian.shortcuts import get_users_with_perms
        users = get_users_with_perms(obj.site, only_with_perms_in=['access_site'])
        return users.count()
    user_count.short_description = 'Users with Access'
    
    def grant_access_to_all_owners(self, request, queryset):
        """Grant site access to all owners of the organization"""
        from guardian.shortcuts import assign_perm
        
        total_granted = 0
        for org_site in queryset:
            owners = org_site.organization.members.filter(role='owner', is_active=True)
            for member in owners:
                assign_perm('access_site', member.user, org_site.site)
                assign_perm('admin_site', member.user, org_site.site)
                total_granted += 1
        
        self.message_user(
            request,
            f'Granted site access to {total_granted} owner(s).',
            messages.SUCCESS
        )
    grant_access_to_all_owners.short_description = "Grant access to all organization owners"


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(BaseModelAdmin, SimpleHistoryAdmin):
    """Admin for Organization Invitations"""
    list_display = (
        'email', 'organization', 'role', 'invited_by', 'is_accepted',
        'expires_at', 'status_display', 'created_at'
    )
    list_filter = ('role', 'is_accepted', 'expires_at', 'created_at')
    search_fields = ('email', 'organization__name', 'invited_by__username')
    readonly_fields = (
        'token', 'accepted_by', 'accepted_at', 'status_display',
        'created_at', 'updated_at', 'created_by', 'modified_by'
    )
    
    fieldsets = (
        ('Invitation Details', {
            'fields': ('organization', 'email', 'role', 'invited_by'),
            'description': 'Basic invitation information'
        }),
        ('Message', {
            'fields': ('message',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('token', 'is_accepted', 'accepted_by', 'accepted_at', 'expires_at', 'status_display'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at', 'created_by', 'modified_by'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['resend_invitations', 'extend_invitations', 'cancel_invitations']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'organization', 'invited_by', 'accepted_by', 'created_by', 'modified_by'
        )
    
    def status_display(self, obj):
        """Display invitation status with color"""
        if obj.is_accepted:
            return format_html('<span style="color: green;">✓ Accepted</span>')
        elif obj.is_expired():
            return format_html('<span style="color: red;">✗ Expired</span>')
        else:
            return format_html('<span style="color: orange;">⏳ Pending</span>')
    status_display.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Auto-send invitation email for new invitations"""
        is_new = not obj.pk
        
        # Save the invitation first
        super().save_model(request, obj, form, change)
        
        # Send invitation email for new invitations
        if is_new:
            from .tasks import send_organization_invitation_email
            try:
                send_organization_invitation_email.delay(obj.id)
                self.message_user(
                    request,
                    f'Invitation created and email queued for {obj.email}',
                    messages.SUCCESS
                )
            except Exception as e:
                self.message_user(
                    request,
                    f'Invitation created but email failed to queue: {str(e)}',
                    messages.WARNING
                )
    
    def resend_invitations(self, request, queryset):
        """Bulk action to resend pending invitations"""
        from .tasks import send_organization_invitation_email
        
        pending_invitations = queryset.filter(
            is_accepted=False, 
            expires_at__gt=timezone.now()
        )
        
        for invitation in pending_invitations:
            send_organization_invitation_email.delay(invitation.id)
        
        count = pending_invitations.count()
        self.message_user(
            request,
            f'Queued {count} invitation email(s) for sending.',
            messages.SUCCESS
        )
    resend_invitations.short_description = "Resend pending invitations"
    
    def extend_invitations(self, request, queryset):
        """Bulk action to extend invitation expiry"""
        from datetime import timedelta
        
        updated = queryset.filter(is_accepted=False).update(
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        self.message_user(
            request,
            f'Extended expiry for {updated} invitation(s) by 7 days.',
            messages.SUCCESS
        )
    extend_invitations.short_description = "Extend invitation expiry by 7 days"
    
    def cancel_invitations(self, request, queryset):
        """Bulk action to cancel invitations"""
        count = queryset.filter(is_accepted=False).count()
        queryset.filter(is_accepted=False).delete()
        
        self.message_user(
            request,
            f'Cancelled {count} pending invitation(s).',
            messages.SUCCESS
        )
    cancel_invitations.short_description = "Cancel pending invitations"

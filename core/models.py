from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from datetime import timedelta
import secrets
from simple_history.models import HistoricalRecords


class BaseModel(models.Model):
    """
    Abstract base model with common fields for all models.
    
    Provides timestamp tracking and user tracking fields that are commonly
    needed across most models in the application.
    """
    # Timestamp fields
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this record was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When this record was last updated")
    
    # User tracking fields (nullable to handle system-created records)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_%(class)s_set',
        help_text="User who created this record"
    )
    modified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='modified_%(class)s_set',
        help_text="User who last modified this record"
    )
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_%(class)s_set',
        help_text="User this record is assigned to"
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def __str__(self):
        """Default string representation showing creation info"""
        return f"{self.__class__.__name__} created {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class Site(TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)
    
    # Optional: Add additional fields for your tenant
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Enable auto schema creation - django-tenants will handle this
    auto_create_schema = True
    
    # Historical records
    history = HistoricalRecords()
    
    class Meta:
        permissions = [
            ('access_site', 'Can access site'),
            ('manage_site_users', 'Can manage site users'),
            ('admin_site', 'Can administer site'),
        ]
    
    def __str__(self):
        return self.name


class Domain(DomainMixin):
    # Historical records
    history = HistoricalRecords()


# Organization Models (Public Schema Only)

class Organization(BaseModel):
    """
    Organization model - custom implementation without django-organizations.
    Supports multiple owners and Guardian permissions.
    """
    name = models.CharField(max_length=200, help_text="Organization name")
    slug = models.SlugField(max_length=200, unique=True, help_text="URL-friendly organization identifier")
    description = models.TextField(blank=True, null=True, help_text="Organization description")
    
    # Contact information
    website = models.URLField(blank=True, null=True, help_text="Organization website")
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Organization phone")
    email = models.EmailField(blank=True, null=True, help_text="Organization contact email")
    address = models.TextField(blank=True, null=True, help_text="Organization address")
    
    # Subscription and limits
    subscription_plan = models.CharField(
        max_length=50,
        choices=[
            ('free', 'Free'),
            ('basic', 'Basic'),
            ('professional', 'Professional'),
            ('enterprise', 'Enterprise'),
        ],
        default='free',
        help_text="Current subscription plan"
    )
    max_sites = models.PositiveIntegerField(default=1, help_text="Maximum sites allowed")
    max_members = models.PositiveIntegerField(default=5, help_text="Maximum members allowed")
    
    # Status and verification
    is_active = models.BooleanField(default=True, help_text="Organization is active")
    is_verified = models.BooleanField(default=False, help_text="Organization is verified")
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    settings = models.JSONField(default=dict, blank=True, help_text="Organization settings")
    
    # Historical records
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        permissions = [
            ('manage_organization', 'Can manage organization'),
            ('invite_members', 'Can invite members to organization'),
            ('manage_sites', 'Can manage organization sites'),
        ]
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_verified']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)
    
    def generate_unique_slug(self):
        """Generate a unique slug for the organization"""
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1
        
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def get_member_count(self):
        """Get total member count"""
        return self.members.count()
    
    def get_owner_count(self):
        """Get total owner count"""
        return self.members.filter(role='owner').count()
    
    def get_site_count(self):
        """Get total site count"""
        return self.organization_sites.count()
    
    def can_add_member(self):
        """Check if organization can add more members"""
        return self.get_member_count() < self.max_members
    
    def can_add_site(self):
        """Check if organization can add more sites"""
        return self.get_site_count() < self.max_sites


class OrganizationMember(BaseModel):
    """
    Organization membership model.
    Links users to organizations with roles (member/owner).
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members',
        help_text="Organization"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
        help_text="User"
    )
    
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('owner', 'Owner'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='member',
        help_text="Role in organization"
    )
    
    # Additional member information
    title = models.CharField(max_length=100, blank=True, null=True, help_text="Job title")
    department = models.CharField(max_length=100, blank=True, null=True, help_text="Department")
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Phone number")
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Member is active")
    joined_at = models.DateTimeField(auto_now_add=True, help_text="When user joined")
    last_active = models.DateTimeField(blank=True, null=True, help_text="Last activity time")
    
    # Historical records
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'Organization Member'
        verbose_name_plural = 'Organization Members'
        unique_together = ('organization', 'user')
        indexes = [
            models.Index(fields=['organization', 'role']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.organization.name} ({self.get_role_display()})"
    
    def is_owner(self):
        """Check if member is an owner"""
        return self.role == 'owner'
    
    def update_last_active(self):
        """Update last active timestamp"""
        self.last_active = timezone.now()
        self.save(update_fields=['last_active'])


class OrganizationSite(BaseModel):
    """
    Links organizations to their tenant sites.
    Sites are accessed via Guardian permissions.
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='organization_sites',
        help_text="Organization that owns this site"
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='organization_sites',
        help_text="Tenant site"
    )
    
    # Site configuration
    is_primary = models.BooleanField(default=False, help_text="Primary site for organization")
    site_role = models.CharField(
        max_length=50,
        choices=[
            ('production', 'Production'),
            ('staging', 'Staging'),
            ('development', 'Development'),
            ('testing', 'Testing'),
        ],
        default='production',
        help_text="Site environment role"
    )
    
    # Access settings
    site_settings = models.JSONField(default=dict, blank=True, help_text="Site-specific settings")
    is_active = models.BooleanField(default=True, help_text="Site is active")
    
    # Historical records
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'Organization Site'
        verbose_name_plural = 'Organization Sites'
        unique_together = ('organization', 'site')
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['site', 'is_active']),
        ]
    
    def __str__(self):
        primary = " (Primary)" if self.is_primary else ""
        return f"{self.organization.name} → {self.site.name}{primary}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary site per organization
        if self.is_primary:
            OrganizationSite.objects.filter(
                organization=self.organization,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class OrganizationInvitation(BaseModel):
    """
    Handles email invitations to join organizations.
    Uses token-based invitation system with expiration.
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invitations',
        help_text="Organization to invite user to"
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        help_text="User who sent the invitation"
    )
    
    # Invitation details
    email = models.EmailField(help_text="Email address of invited user")
    role = models.CharField(
        max_length=20,
        choices=OrganizationMember.ROLE_CHOICES,
        default='member',
        help_text="Role to assign when invitation is accepted"
    )
    
    # Token and status
    token = models.CharField(max_length=64, unique=True, help_text="Invitation token")
    is_accepted = models.BooleanField(default=False, help_text="Invitation has been accepted")
    accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_invitations',
        help_text="User who accepted invitation"
    )
    accepted_at = models.DateTimeField(blank=True, null=True, help_text="When invitation was accepted")
    expires_at = models.DateTimeField(help_text="When invitation expires")
    
    # Optional message and metadata
    message = models.TextField(blank=True, null=True, help_text="Personal message from inviter")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional invitation metadata")
    
    # Historical records
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'Organization Invitation'
        verbose_name_plural = 'Organization Invitations'
        unique_together = ('organization', 'email')
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email', 'is_accepted']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['organization', 'is_accepted']),
        ]
    
    def __str__(self):
        status = "Accepted" if self.is_accepted else "Pending"
        return f"{self.email} → {self.organization.name} ({status})"
    
    def save(self, *args, **kwargs):
        # Generate token if not set
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        
        # Set expiration if not set
        if not self.expires_at:
            from django.conf import settings
            days = getattr(settings, 'INVITATION_EXPIRES_DAYS', 7)
            self.expires_at = timezone.now() + timedelta(days=days)
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate invitation"""
        super().clean()
        
        # Check if user is already a member
        if User.objects.filter(
            email=self.email,
            organization_memberships__organization=self.organization,
            organization_memberships__is_active=True
        ).exists():
            raise ValidationError(f"User with email {self.email} is already a member of {self.organization.name}")
        
        # Check if there's already a pending invitation
        if OrganizationInvitation.objects.filter(
            organization=self.organization,
            email=self.email,
            is_accepted=False,
            expires_at__gt=timezone.now()
        ).exclude(pk=self.pk).exists():
            raise ValidationError(f"There is already a pending invitation for {self.email}")
    
    def is_expired(self):
        """Check if invitation has expired"""
        if self.expires_at is None:
            return False  # If no expiry date set, consider it as not expired
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if invitation is still valid"""
        return not self.is_accepted and not self.is_expired()
    
    def accept(self, user):
        """Accept invitation for a user"""
        if not self.is_valid():
            raise ValidationError("Invitation is no longer valid")
        
        if user.email.lower() != self.email.lower():
            raise ValidationError("User email must match invitation email")
        
        # Check organization member limits
        if not self.organization.can_add_member():
            raise ValidationError(f"Organization has reached its member limit of {self.organization.max_members}")
        
        # Create organization member
        member, created = OrganizationMember.objects.get_or_create(
            organization=self.organization,
            user=user,
            defaults={
                'role': self.role,
                'is_active': True,
                'created_by': self.invited_by,
            }
        )
        
        if not created:
            # Reactivate if was inactive
            if not member.is_active:
                member.is_active = True
                member.role = self.role
                member.save()
        
        # Assign organization permissions via Guardian
        from guardian.shortcuts import assign_perm
        assign_perm('view_organization', user, self.organization)
        
        # If owner role, assign management permissions
        if self.role == 'owner':
            assign_perm('manage_organization', user, self.organization)
            assign_perm('invite_members', user, self.organization)
            assign_perm('manage_sites', user, self.organization)
        
        # Mark invitation as accepted
        self.is_accepted = True
        self.accepted_by = user
        self.accepted_at = timezone.now()
        self.modified_by = user
        self.save()
        
        return member
    
    def generate_token(self):
        """Generate a new invitation token"""
        self.token = secrets.token_urlsafe(32)
    
    def send_invitation_email(self):
        """Send invitation email to the invited user"""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        # Build accept URL (this would need to be configured based on your frontend)
        accept_url = f"{settings.FRONTEND_URL}/accept-invitation/{self.token}/" if hasattr(settings, 'FRONTEND_URL') else f"http://localhost:8000/api/organization-invitations/accept_invitation/"
        
        # Context for email templates
        context = {
            'invitation': self,
            'organization': self.organization,
            'invited_by': self.invited_by,
            'accept_url': accept_url,
            'message': self.message,
        }
        
        # Render email templates
        html_message = render_to_string('emails/organization_invitation.html', context)
        text_message = render_to_string('emails/organization_invitation.txt', context)
        
        # Send email
        subject = f"Invitation to join {self.organization.name} on Taruvi"
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.email],
            html_message=html_message,
            fail_silently=False
        )

from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from guardian.shortcuts import get_perms, get_objects_for_user

from .models import (
    Site, Domain, Organization, OrganizationMember, 
    OrganizationSite, OrganizationInvitation
)


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_active']
        read_only_fields = ['id', 'username', 'full_name']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class SiteSerializer(serializers.ModelSerializer):
    """Site/Tenant serializer"""
    user_permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = Site
        fields = ['schema_name', 'name', 'description', 'is_active', 'created_on', 'user_permissions']
        read_only_fields = ['schema_name', 'created_on', 'user_permissions']
    
    def get_user_permissions(self, obj):
        """Get current user's permissions on this site"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return get_perms(request.user, obj)
        return []


class DomainSerializer(serializers.ModelSerializer):
    """Domain serializer"""
    site_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = Domain
        fields = ['domain', 'tenant', 'site_name', 'is_primary']


# Organization Serializers

class OrganizationSerializer(serializers.ModelSerializer):
    """Organization serializer with computed fields"""
    member_count = serializers.SerializerMethodField()
    owner_count = serializers.SerializerMethodField()
    site_count = serializers.SerializerMethodField()
    can_add_member = serializers.SerializerMethodField()
    can_add_site = serializers.SerializerMethodField()
    user_permissions = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'email', 'website', 'phone', 'address',
            'subscription_plan', 'max_sites', 'max_members',
            'is_active', 'is_verified', 'verified_at', 'settings',
            'member_count', 'owner_count', 'site_count', 
            'can_add_member', 'can_add_site', 'user_permissions', 'user_role',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'verified_at', 'member_count', 'owner_count', 'site_count',
            'can_add_member', 'can_add_site', 'user_permissions', 'user_role',
            'created_at', 'updated_at'
        ]
    
    def get_member_count(self, obj):
        return obj.get_member_count()
    
    def get_owner_count(self, obj):
        return obj.get_owner_count()
    
    def get_site_count(self, obj):
        return obj.get_site_count()
    
    def get_can_add_member(self, obj):
        return obj.can_add_member()
    
    def get_can_add_site(self, obj):
        return obj.can_add_site()
    
    def get_user_permissions(self, obj):
        """Get current user's permissions on this organization"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return get_perms(request.user, obj)
        return []
    
    def get_user_role(self, obj):
        """Get current user's role in this organization"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                member = obj.members.get(user=request.user, is_active=True)
                return member.role
            except OrganizationMember.DoesNotExist:
                return None
        return None


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating organizations"""
    class Meta:
        model = Organization
        fields = ['name', 'description', 'email', 'website', 'phone', 'address']
    
    def create(self, validated_data):
        """Create organization and make creator an owner"""
        # Set created_by from request
        validated_data['created_by'] = self.context['request'].user
        
        # Create organization
        organization = super().create(validated_data)
        
        # Create organization member for creator as owner
        OrganizationMember.objects.create(
            organization=organization,
            user=self.context['request'].user,
            role='owner',
            is_active=True,
            created_by=self.context['request'].user,
        )
        
        # Assign organization permissions via Guardian
        from guardian.shortcuts import assign_perm
        user = self.context['request'].user
        assign_perm('view_organization', user, organization)
        assign_perm('manage_organization', user, organization)
        assign_perm('invite_members', user, organization)
        assign_perm('manage_sites', user, organization)
        
        return organization


class OrganizationMemberSerializer(serializers.ModelSerializer):
    """Organization member serializer"""
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    is_owner = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganizationMember
        fields = [
            'id', 'organization', 'organization_name', 'user', 'user_id', 'role',
            'title', 'department', 'phone', 'is_active', 'is_owner',
            'joined_at', 'last_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization_name', 'is_owner', 'joined_at', 'last_active',
            'created_at', 'updated_at'
        ]
    
    def get_is_owner(self, obj):
        return obj.is_owner()
    
    def validate_user_id(self, value):
        """Validate user exists"""
        if value:
            try:
                User.objects.get(id=value)
            except User.DoesNotExist:
                raise serializers.ValidationError("User does not exist")
        return value
    
    def create(self, validated_data):
        """Create organization member"""
        user_id = validated_data.pop('user_id', None)
        if user_id:
            validated_data['user'] = User.objects.get(id=user_id)
        
        validated_data['created_by'] = self.context['request'].user
        member = super().create(validated_data)
        
        # Assign basic organization permissions
        from guardian.shortcuts import assign_perm
        assign_perm('view_organization', member.user, member.organization)
        
        # If owner, assign additional permissions
        if member.role == 'owner':
            assign_perm('manage_organization', member.user, member.organization)
            assign_perm('invite_members', member.user, member.organization)
            assign_perm('manage_sites', member.user, member.organization)
        
        return member


class OrganizationSiteSerializer(serializers.ModelSerializer):
    """Organization site serializer"""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    site = SiteSerializer(read_only=True)
    site_id = serializers.CharField(source='site.schema_name', write_only=True, required=False)
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganizationSite
        fields = [
            'id', 'organization', 'organization_name', 'site', 'site_id',
            'is_primary', 'site_role', 'is_active', 'site_settings',
            'user_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization_name', 'user_count', 'created_at', 'updated_at'
        ]
    
    def get_user_count(self, obj):
        """Get count of users with access to this site"""
        from guardian.shortcuts import get_users_with_perms
        users = get_users_with_perms(obj.site, only_with_perms_in=['access_site'])
        return users.count()
    
    def validate_site_id(self, value):
        """Validate site exists"""
        if value:
            try:
                Site.objects.get(schema_name=value)
            except Site.DoesNotExist:
                raise serializers.ValidationError("Site does not exist")
        return value
    
    def create(self, validated_data):
        """Create organization site"""
        site_id = validated_data.pop('site_id', None)
        if site_id:
            validated_data['site'] = Site.objects.get(schema_name=site_id)
        
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class OrganizationInvitationSerializer(serializers.ModelSerializer):
    """Organization invitation serializer"""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    invited_by = UserSerializer(read_only=True)
    accepted_by = UserSerializer(read_only=True)
    is_expired = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganizationInvitation
        fields = [
            'id', 'organization', 'organization_name', 'email', 'role',
            'invited_by', 'accepted_by', 'token', 'is_accepted', 'accepted_at',
            'expires_at', 'message', 'is_expired', 'is_valid',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization_name', 'invited_by', 'accepted_by', 'token',
            'is_accepted', 'accepted_at', 'is_expired', 'is_valid',
            'created_at', 'updated_at'
        ]
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_is_valid(self, obj):
        return obj.is_valid()
    
    def create(self, validated_data):
        """Create invitation and send email asynchronously"""
        validated_data['invited_by'] = self.context['request'].user
        validated_data['created_by'] = self.context['request'].user
        invitation = super().create(validated_data)
        
        # Send invitation email asynchronously
        from .tasks import send_organization_invitation_email
        send_organization_invitation_email.delay(invitation.id)
        
        return invitation


class AcceptInvitationSerializer(serializers.Serializer):
    """Serializer for accepting invitations"""
    token = serializers.CharField(max_length=64)
    
    def validate_token(self, value):
        """Validate invitation token"""
        try:
            invitation = OrganizationInvitation.objects.get(token=value)
            if not invitation.is_valid():
                raise serializers.ValidationError("Invitation is no longer valid")
            return value
        except OrganizationInvitation.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation token")
    
    def save(self):
        """Accept invitation and send welcome email"""
        token = self.validated_data['token']
        user = self.context['request'].user
        
        invitation = OrganizationInvitation.objects.get(token=token)
        member = invitation.accept(user)
        
        # Send welcome email asynchronously
        from .tasks import send_organization_welcome_email
        send_organization_welcome_email.delay(member.id)
        
        return member


class SitePermissionSerializer(serializers.Serializer):
    """Serializer for managing site permissions"""
    user = serializers.IntegerField(source='user_id', help_text="User ID")
    permission = serializers.ChoiceField(
        choices=[
            ('access_site', 'Access Site'),
            ('manage_site_users', 'Manage Site Users'),
            ('admin_site', 'Admin Site'),
        ],
        help_text="Permission to grant"
    )
    
    def validate_user(self, value):
        """Validate user exists and is organization member"""
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        
        # Check if user is member of organization that owns the site
        site = self.context['site']
        organization = self.context['organization']
        
        if not organization.members.filter(user=user, is_active=True).exists():
            raise serializers.ValidationError("User is not a member of the organization")
        
        return value
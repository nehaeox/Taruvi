from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from guardian.shortcuts import assign_perm, remove_perm, get_objects_for_user, get_perms
from guardian.decorators import permission_required_or_403
from django_tenants.utils import schema_context

from celery.result import AsyncResult
from .tasks import debug_task, send_email_task, process_data_task
from .decorators import api_rate_limit, auth_rate_limit, burst_rate_limit, log_api_access
from django.db import connection

from .models import Organization, OrganizationMember, OrganizationSite, OrganizationInvitation, Site, Domain
from .serializers import (
    OrganizationSerializer, OrganizationMemberSerializer, 
    OrganizationSiteSerializer, OrganizationInvitationSerializer,
    AcceptInvitationSerializer, SitePermissionSerializer
)

import json
import os
import threading


@api_view(['POST'])
@api_rate_limit()
@burst_rate_limit()
@log_api_access('test_celery_task')
def test_celery_task(request):
    """Test endpoint to trigger Celery tasks"""
    task_type = request.data.get('task_type', 'debug')
    
    if task_type == 'debug':
        task = debug_task.delay()
    elif task_type == 'email':
        task = send_email_task.delay(
            subject='Test Email',
            message='This is a test email from the API',
            recipient_list=['test@example.com']
        )
    elif task_type == 'process_data':
        test_data = request.data.get('data', {'test': True})
        task = process_data_task.delay(test_data)
    else:
        return Response({'error': 'Invalid task type'}, status=400)
    
    return Response({
        'task_id': task.id,
        'task_type': task_type,
        'status': 'Task started'
    })


@api_view(['GET'])
@api_rate_limit()
@log_api_access('task_status')
def task_status(request, task_id):
    """Get status of a Celery task"""
    result = AsyncResult(task_id)
    
    response_data = {
        'task_id': task_id,
        'status': result.status,
        'ready': result.ready(),
    }
    
    if result.ready():
        if result.successful():
            response_data['result'] = result.result
        else:
            response_data['error'] = str(result.result)
    
    return Response(response_data)


def tenant_info(request):
    """Simple view to show current tenant information"""
    current_tenant = connection.tenant
    schema_name = connection.schema_name
    
    html = f"""
    <html>
    <head><title>Tenant Info</title></head>
    <body>
        <h1>Tenant Information</h1>
        <p><strong>Schema:</strong> {schema_name}</p>
        <p><strong>Tenant:</strong> {current_tenant.name if hasattr(current_tenant, 'name') else 'N/A'}</p>
        <p><strong>Domain:</strong> {request.get_host()}</p>
        <p><strong>Request Path:</strong> {request.path}</p>
        <hr>
        <p><a href="/admin/">Go to Admin</a></p>
    </body>
    </html>
    """
    return HttpResponse(html)


def home(request):
    """Simple home view"""
    return tenant_info(request)


class GuardianPermissionMixin:
    """Mixin to add Guardian permission filtering to viewsets"""
    
    def get_queryset(self):
        """Filter queryset based on Guardian permissions"""
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset()
        
        # Get objects user has permission to view
        model_class = self.queryset.model
        permission = f'{model_class._meta.app_label}.view_{model_class._meta.model_name}'
        return get_objects_for_user(user, permission, klass=model_class)


class OrganizationViewSet(GuardianPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for Organization management with Guardian permissions
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    
    def perform_create(self, serializer):
        """Create organization and assign creator as owner with all permissions"""
        organization = serializer.save(created_by=self.request.user)
        
        # Create membership for creator as owner
        OrganizationMember.objects.create(
            organization=organization,
            user=self.request.user,
            role='owner',
            is_active=True,
            created_by=self.request.user
        )
        
        # Assign all Guardian permissions to creator
        permissions = ['view_organization', 'change_organization', 'delete_organization', 'manage_organization']
        for perm in permissions:
            assign_perm(perm, self.request.user, organization)
    
    @action(detail=True, methods=['get'])
    def members(self, request, slug=None):
        """Get organization members"""
        organization = self.get_object()
        
        # Check permission
        if not request.user.has_perm('manage_organization', organization):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        members = OrganizationMember.objects.filter(organization=organization)
        serializer = OrganizationMemberSerializer(members, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, slug=None):
        """Add member to organization"""
        organization = self.get_object()
        
        # Check permission
        if not request.user.has_perm('manage_organization', organization):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'member')
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user is already a member
        if OrganizationMember.objects.filter(organization=organization, user=user).exists():
            return Response({'error': 'User is already a member'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create membership
        member = OrganizationMember.objects.create(
            organization=organization,
            user=user,
            role=role,
            is_active=True,
            created_by=request.user
        )
        
        # Assign Guardian permissions based on role
        if role == 'owner':
            permissions = ['view_organization', 'change_organization', 'delete_organization', 'manage_organization']
        else:
            permissions = ['view_organization']
        
        for perm in permissions:
            assign_perm(perm, user, organization)
        
        serializer = OrganizationMemberSerializer(member, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def remove_member(self, request, slug=None):
        """Remove member from organization"""
        organization = self.get_object()
        
        # Check permission
        if not request.user.has_perm('manage_organization', organization):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        
        try:
            member = OrganizationMember.objects.get(organization=organization, user_id=user_id)
        except OrganizationMember.DoesNotExist:
            return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Cannot remove yourself if you're the only owner
        if (member.user == request.user and member.role == 'owner' and 
            OrganizationMember.objects.filter(organization=organization, role='owner').count() == 1):
            return Response({'error': 'Cannot remove the only owner'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Remove Guardian permissions
        permissions = ['view_organization', 'change_organization', 'delete_organization', 'manage_organization']
        for perm in permissions:
            remove_perm(perm, member.user, organization)
        
        # Also remove site permissions for this organization
        org_sites = OrganizationSite.objects.filter(organization=organization)
        for org_site in org_sites:
            site_permissions = ['view_client', 'change_client', 'delete_client']
            for perm in site_permissions:
                remove_perm(perm, member.user, org_site.site)
        
        member.delete()
        return Response({'message': 'Member removed successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def sites(self, request, slug=None):
        """Get organization sites"""
        organization = self.get_object()
        
        # Check permission
        if not request.user.has_perm('view_organization', organization):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        sites = OrganizationSite.objects.filter(organization=organization)
        serializer = OrganizationSiteSerializer(sites, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_site(self, request, slug=None):
        """Add site to organization"""
        organization = self.get_object()
        
        # Check permission
        if not request.user.has_perm('manage_organization', organization):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        site_id = request.data.get('site_id')
        
        try:
            site = Site.objects.get(id=site_id)
        except Site.DoesNotExist:
            return Response({'error': 'Site not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if site is already assigned to this organization
        if OrganizationSite.objects.filter(organization=organization, site=site).exists():
            return Response({'error': 'Site is already assigned to this organization'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check organization limits
        current_sites_count = OrganizationSite.objects.filter(organization=organization).count()
        if current_sites_count >= organization.max_sites:
            return Response({'error': 'Organization site limit reached'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create organization site
        org_site = OrganizationSite.objects.create(
            organization=organization,
            site=site,
            created_by=request.user
        )
        
        serializer = OrganizationSiteSerializer(org_site, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def grant_site_access(self, request, slug=None):
        """Grant site access to organization member"""
        organization = self.get_object()
        
        # Check permission
        if not request.user.has_perm('manage_organization', organization):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        site_id = request.data.get('site_id')
        permissions_to_grant = request.data.get('permissions', ['view_client'])
        
        try:
            user = User.objects.get(id=user_id)
            site = Site.objects.get(id=site_id)
        except (User.DoesNotExist, Site.DoesNotExist):
            return Response({'error': 'User or Site not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user is organization member
        if not OrganizationMember.objects.filter(organization=organization, user=user, is_active=True).exists():
            return Response({'error': 'User is not an active organization member'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if site belongs to organization
        if not OrganizationSite.objects.filter(organization=organization, site=site).exists():
            return Response({'error': 'Site does not belong to this organization'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Grant Guardian permissions
        valid_permissions = ['view_client', 'change_client', 'delete_client']
        granted_permissions = []
        
        for perm in permissions_to_grant:
            if perm in valid_permissions:
                assign_perm(perm, user, site)
                granted_permissions.append(perm)
        
        return Response({
            'message': 'Site access granted successfully',
            'granted_permissions': granted_permissions
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def revoke_site_access(self, request, slug=None):
        """Revoke site access from organization member"""
        organization = self.get_object()
        
        # Check permission
        if not request.user.has_perm('manage_organization', organization):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        site_id = request.data.get('site_id')
        permissions_to_revoke = request.data.get('permissions', ['view_client', 'change_client', 'delete_client'])
        
        try:
            user = User.objects.get(id=user_id)
            site = Site.objects.get(id=site_id)
        except (User.DoesNotExist, Site.DoesNotExist):
            return Response({'error': 'User or Site not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Revoke Guardian permissions
        revoked_permissions = []
        for perm in permissions_to_revoke:
            remove_perm(perm, user, site)
            revoked_permissions.append(perm)
        
        return Response({
            'message': 'Site access revoked successfully',
            'revoked_permissions': revoked_permissions
        }, status=status.HTTP_200_OK)


class OrganizationMemberViewSet(GuardianPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for Organization Member management
    """
    queryset = OrganizationMember.objects.all()
    serializer_class = OrganizationMemberSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter members based on organization access"""
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        
        # Get organizations user has access to
        organizations = get_objects_for_user(user, 'view_organization', klass=Organization)
        return OrganizationMember.objects.filter(organization__in=organizations)
    
    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """Change member role"""
        member = self.get_object()
        organization = member.organization
        
        # Check permission
        if not request.user.has_perm('manage_organization', organization):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        new_role = request.data.get('role')
        if new_role not in ['member', 'owner']:
            return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)
        
        # If demoting from owner to member, ensure there's at least one owner left
        if (member.role == 'owner' and new_role == 'member' and 
            OrganizationMember.objects.filter(organization=organization, role='owner').count() == 1):
            return Response({'error': 'Cannot demote the only owner'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update role
        old_role = member.role
        member.role = new_role
        member.modified_by = request.user
        member.save()
        
        # Update Guardian permissions
        if new_role == 'owner':
            permissions = ['view_organization', 'change_organization', 'delete_organization', 'manage_organization']
            for perm in permissions:
                assign_perm(perm, member.user, organization)
        else:
            # Remove management permissions but keep view
            permissions_to_remove = ['change_organization', 'delete_organization', 'manage_organization']
            for perm in permissions_to_remove:
                remove_perm(perm, member.user, organization)
        
        return Response({
            'message': f'Role changed from {old_role} to {new_role}',
            'member': OrganizationMemberSerializer(member, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class OrganizationSiteViewSet(GuardianPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for Organization Site management
    """
    queryset = OrganizationSite.objects.all()
    serializer_class = OrganizationSiteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter sites based on organization access"""
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        
        # Get organizations user has access to
        organizations = get_objects_for_user(user, 'view_organization', klass=Organization)
        return OrganizationSite.objects.filter(organization__in=organizations)
    
    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """Get site permissions for organization members"""
        org_site = self.get_object()
        organization = org_site.organization
        
        # Check permission
        if not request.user.has_perm('view_organization', organization):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        members = OrganizationMember.objects.filter(organization=organization, is_active=True)
        permissions_data = []
        
        for member in members:
            user_perms = get_perms(member.user, org_site.site)
            permissions_data.append({
                'user_id': member.user.id,
                'username': member.user.username,
                'role': member.role,
                'permissions': list(user_perms)
            })
        
        return Response(permissions_data)


class OrganizationInvitationViewSet(GuardianPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for Organization Invitation management
    """
    queryset = OrganizationInvitation.objects.all()
    serializer_class = OrganizationInvitationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter invitations based on organization access"""
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        
        # Get organizations user has access to
        organizations = get_objects_for_user(user, 'manage_organization', klass=Organization)
        return OrganizationInvitation.objects.filter(organization__in=organizations)
    
    def perform_create(self, serializer):
        """Create invitation with proper permissions check"""
        organization = serializer.validated_data['organization']
        
        # Check permission
        if not self.request.user.has_perm('manage_organization', organization):
            raise PermissionError('Permission denied')
        
        # Check organization member limits
        current_members = OrganizationMember.objects.filter(organization=organization, is_active=True).count()
        pending_invitations = OrganizationInvitation.objects.filter(organization=organization, status='pending').count()
        
        if current_members + pending_invitations >= organization.max_members:
            raise ValueError('Organization member limit reached')
        
        serializer.save(invited_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def accept_invitation(self, request):
        """Accept organization invitation"""
        serializer = AcceptInvitationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                member = serializer.save()
                return Response({
                    'message': 'Invitation accepted successfully',
                    'member': OrganizationMemberSerializer(member, context={'request': request}).data
                }, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Resend invitation email"""
        invitation = self.get_object()
        
        # Check permission
        if not request.user.has_perm('manage_organization', invitation.organization):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if invitation.status != 'pending':
            return Response({'error': 'Cannot resend non-pending invitation'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate new token and send email
        invitation.generate_token()
        invitation.save()
        invitation.send_invitation_email()
        
        return Response({'message': 'Invitation resent successfully'}, status=status.HTTP_200_OK)


class SitePermissionViewSet(viewsets.ViewSet):
    """
    ViewSet for managing site permissions via Guardian
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """List user's site permissions"""
        user = request.user
        sites_with_perms = []
        
        # Get all sites user has any permission on
        sites = get_objects_for_user(user, ['view_client', 'change_client', 'delete_client'], 
                                   klass=Site, any_perm=True)
        
        for site in sites:
            user_perms = get_perms(user, site)
            sites_with_perms.append({
                'site_id': site.id,
                'site_name': site.name,
                'schema_name': site.schema_name,
                'permissions': list(user_perms)
            })
        
        return Response(sites_with_perms)
    
    @action(detail=False, methods=['post'])
    def check_permission(self, request):
        """Check if user has specific permission on site"""
        serializer = SitePermissionSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            site_id = serializer.validated_data['site_id']
            permission = serializer.validated_data['permission']
            
            try:
                site = Site.objects.get(id=site_id)
                has_permission = user.has_perm(permission, site)
                
                return Response({
                    'has_permission': has_permission,
                    'user_id': user.id,
                    'site_id': site_id,
                    'permission': permission
                })
            except Site.DoesNotExist:
                return Response({'error': 'Site not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

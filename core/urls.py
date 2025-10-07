from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView, TokenVerifyView,
)
from . import views

# API Router
router = DefaultRouter()

# Register organization API viewsets
router.register('organizations', views.OrganizationViewSet)
router.register('organization-members', views.OrganizationMemberViewSet)
router.register('organization-sites', views.OrganizationSiteViewSet)
router.register('organization-invitations', views.OrganizationInvitationViewSet)
router.register('site-permissions', views.SitePermissionViewSet, basename='site-permission')

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
    # Health checks will be handled by django-health-check at /ht/ endpoint
    
    # Task endpoints
    path('tasks/', include([
        path('test/', views.test_celery_task, name='test_celery_task'),
        path('status/<str:task_id>/', views.task_status, name='task_status'),
    ])),
    
    # JWT Authentication
    path('auth/jwt/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/jwt/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/jwt/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/jwt/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    # Session Authentication (for browsable API)
    path('auth/', include('rest_framework.urls')),
]
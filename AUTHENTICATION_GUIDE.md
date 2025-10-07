# Taruvi.cloud Multi-Tenant Authentication Guide

This guide explains how the multi-tenant authentication system works in Taruvi.cloud, leveraging Django-allauth's built-in functionality with tenant-scoped configurations.

## Architecture Overview

### Multi-Tenant Authentication Strategy

Taruvi.cloud implements **schema-based multi-tenancy** where each client/organization has its own database schema, allowing for:
- **Platform-level authentication management** (in shared schema)
- **Tenant-specific user authentication** (in tenant schemas)
- **Extensible OAuth provider support** (Google, GitHub, Microsoft, OpenID Connect, Keycloak, Okta)

### Key Components

1. **Django-allauth** - Provides built-in authentication, social login, and admin interfaces
2. **Django-tenants** - Enables schema-based multi-tenancy
3. **SiteAuthConfig** - Custom model linking tenants to authentication preferences
4. **Tenant-aware SocialApp Admin** - Custom admin for managing OAuth providers per tenant

## How It Works

### Shared vs Tenant Apps Configuration

**SHARED_APPS** (Platform-wide management):
```python
SHARED_APPS = [
    # ... other apps
    'django.contrib.sites',
    'allauth',
    'allauth.account', 
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.microsoft',
    'allauth.socialaccount.providers.openid_connect',
    'core',  # Contains Client, Domain, SiteAuthConfig models
]
```

**TENANT_APPS** (Site-specific functionality):
```python
TENANT_APPS = [
    'django.contrib.auth',          # Site-specific users and permissions
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'allauth.account',              # Site-specific account management
    'allauth.socialaccount',        # Site-specific social authentication
]
```

### Authentication Flow

1. **Platform Admin** creates clients and domains in the shared schema
2. **Client Admin** configures authentication preferences per tenant
3. **End Users** authenticate using tenant-specific authentication methods
4. **Social Apps** are managed per tenant with automatic isolation

## Admin Interface Guide

### Platform Admin (Public Schema)

Access via: `https://yourdomain.com/admin/` (public schema)

**Client Management:**
- Create new client organizations
- Assign domains to clients
- View all tenants across the platform

**Global Social App Management:**
- Configure platform-wide OAuth providers
- Manage shared authentication settings

### Tenant Admin (Tenant Schema) 

Access via: `https://tenant-domain.com/admin/` (tenant-specific schema)

**Available Admin Interfaces:**

#### 1. Site Authentication Configuration (`core.SiteAuthConfig`)
- **Primary Provider**: Choose default auth method (email, google, github, etc.)
- **Allow Email Signup**: Enable/disable email/password registration
- **Allow Social Login**: Enable/disable OAuth authentication
- **Custom OAuth Settings**: JSON configuration for custom providers (Keycloak, Okta)

#### 2. Social Applications (`socialaccount.SocialApp`) 
- **Tenant-Scoped**: Only shows OAuth apps for current tenant
- **Provider Configuration**: Set up Google, GitHub, Microsoft OAuth
- **Automatic Isolation**: Apps are automatically prefixed with tenant schema name
- **Site Assignment**: Auto-assigns to current tenant's sites

#### 3. User Management (`auth.User`)
- **Tenant-Specific Users**: Only shows users for current tenant
- **Account Settings**: Manage email verification, permissions
- **Social Accounts**: View connected social accounts per user

#### 4. Email Addresses (`account.EmailAddress`)
- **Email Verification**: Manage email confirmation status
- **Primary Email**: Set primary email per user
- **Tenant-Scoped**: Only emails for current tenant users

## Setting Up Authentication Providers

### 1. Google OAuth Setup

**Platform Admin Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Set authorized redirect URIs: `https://your-tenant-domain.com/accounts/google/login/callback/`

**Tenant Admin Steps:**
1. Navigate to tenant admin: `https://tenant-domain.com/admin/`
2. Go to **Social Applications**
3. Click **Add social application**
4. Select **Provider**: Google
5. Enter **Name**: `Google OAuth for [Tenant Name]`
6. Enter **Client ID** and **Secret** from Google Cloud Console
7. Select appropriate **Sites**
8. Save

### 2. GitHub OAuth Setup

**GitHub Steps:**
1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Click **New OAuth App**
3. Set **Authorization callback URL**: `https://tenant-domain.com/accounts/github/login/callback/`

**Tenant Admin Steps:**
1. Add new **Social Application** in tenant admin
2. Select **Provider**: GitHub
3. Configure with GitHub OAuth credentials

### 3. Microsoft OAuth Setup

**Azure AD Steps:**
1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Set **Redirect URI**: `https://tenant-domain.com/accounts/microsoft/login/callback/`

**Tenant Admin Steps:**
1. Add new **Social Application** in tenant admin
2. Select **Provider**: Microsoft
3. Configure with Azure AD credentials

### 4. OpenID Connect (Keycloak/Okta) Setup

**Custom Provider Steps:**
1. In your OpenID Connect provider (Keycloak/Okta):
   - Create new application/client
   - Set redirect URI: `https://tenant-domain.com/accounts/openid_connect/login/callback/`
   - Note down client ID, secret, and OpenID Connect endpoints

**Tenant Admin Steps:**
1. Add new **Social Application** in tenant admin
2. Select **Provider**: OpenID Connect
3. Configure **Client ID** and **Secret**
4. In **Settings** field, add JSON configuration:
```json
{
    "server_url": "https://your-keycloak-domain.com/auth/realms/your-realm",
    "token_endpoint_auth_method": "client_secret_basic"
}
```

## Site Authentication Configuration

### Configuration Options

**SiteAuthConfig Model Fields:**

| Field | Description | Default |
|-------|-------------|---------|
| `client` | Links to tenant/client | Required |
| `allow_email_signup` | Enable email/password registration | `True` |
| `allow_social_login` | Enable OAuth authentication | `True` |
| `primary_provider` | Default authentication method | `'email'` |
| `custom_oauth_settings` | JSON config for custom providers | `{}` |

### Example Configurations

**Email-Only Tenant:**
```python
SiteAuthConfig.objects.create(
    client=tenant_client,
    allow_email_signup=True,
    allow_social_login=False,
    primary_provider='email'
)
```

**Google-First Tenant:**
```python
SiteAuthConfig.objects.create(
    client=tenant_client,
    allow_email_signup=True,
    allow_social_login=True,
    primary_provider='google'
)
```

**Keycloak Enterprise Tenant:**
```python
SiteAuthConfig.objects.create(
    client=tenant_client,
    allow_email_signup=False,
    allow_social_login=True,
    primary_provider='openid_connect',
    custom_oauth_settings={
        "server_url": "https://company-sso.keycloak.com/auth/realms/company",
        "token_endpoint_auth_method": "client_secret_post",
        "scope": ["openid", "profile", "email", "roles"]
    }
)
```

## User Authentication Flow

### For End Users

1. **Visit Tenant Site**: `https://tenant-domain.com/accounts/login/`
2. **Choose Authentication Method**:
   - Email/password (if enabled)
   - Social login buttons (Google, GitHub, etc.)
   - SSO redirect (for enterprise setups)
3. **Complete Authentication**: Follow provider-specific flow
4. **Account Creation**: Automatic account creation for new users
5. **Email Verification**: Required for email-based signups

### Email Templates

Django-allauth provides built-in email templates that can be customized per tenant:
- `account/email/email_confirmation_subject.txt`
- `account/email/email_confirmation_message.txt`
- `socialaccount/email/account_connected_subject.txt`

## Security Features

### Built-in Protections

1. **Tenant Isolation**: Users and apps are automatically isolated by schema
2. **CSRF Protection**: All forms include CSRF tokens
3. **Rate Limiting**: Login attempt limitations per IP
4. **Email Verification**: Mandatory email confirmation for new accounts
5. **Secure Token Storage**: OAuth tokens encrypted in database

### Configuration Security

```python
# Required security settings
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300  # 5 minutes
SOCIALACCOUNT_STORE_TOKENS = True  # For token refresh
```

## Troubleshooting

### Common Issues

**1. Social App Not Showing for Tenant**
- Verify the social app is created in the correct tenant admin
- Check that the app name includes tenant prefix
- Ensure the app is assigned to the correct site

**2. OAuth Redirect URI Mismatch**
- Verify the redirect URI in provider settings matches: `https://tenant-domain.com/accounts/[provider]/login/callback/`
- Check that the tenant domain is correctly configured

**3. Email Verification Not Working**
- Verify SMTP settings are configured
- Check that `ACCOUNT_EMAIL_VERIFICATION = 'mandatory'` is set
- Ensure email templates are accessible

**4. Tenant Users Not Isolated**
- Verify you're accessing the correct tenant subdomain
- Check that `TENANT_APPS` includes `django.contrib.auth`
- Confirm tenant schema is properly created

### Debug Commands

**Check Tenant Configuration:**
```bash
python manage.py shell_plus
from django_tenants.utils import get_tenant_model
Client = get_tenant_model()
for client in Client.objects.all():
    print(f"Client: {client.name}, Schema: {client.schema_name}")
```

**Verify Social Apps:**
```bash
python manage.py tenant_command shell --schema=tenant_name
from allauth.socialaccount.models import SocialApp
print(SocialApp.objects.all())
```

## Advanced Customization

### Custom Authentication Backends

For enterprise SSO integration, create custom authentication backends:

```python
# core/backends.py
from django.contrib.auth.backends import BaseBackend
from allauth.socialaccount.providers.openid_connect.provider import OpenIDConnectProvider

class CustomSSOBackend(BaseBackend):
    def authenticate(self, request, **kwargs):
        # Custom SSO logic
        pass
```

### Dynamic Provider Configuration

Load OAuth provider settings dynamically based on tenant:

```python
# core/provider_config.py
def get_tenant_provider_config(tenant, provider_name):
    config = tenant.auth_config.custom_oauth_settings.get(provider_name, {})
    return config
```

This authentication system provides a robust, scalable solution for multi-tenant SaaS applications with flexible authentication options per tenant while leveraging Django-allauth's battle-tested functionality.
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import Client, Domain, SiteAuthConfig


User = get_user_model()


class Command(BaseCommand):
    help = 'Set up development environment with public tenant and admin user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-username',
            default='admin',
            help='Username for the admin user (default: admin)'
        )
        parser.add_argument(
            '--admin-email',
            default='admin@example.com',
            help='Email for the admin user (default: admin@example.com)'
        )
        parser.add_argument(
            '--admin-password',
            default='admin123',
            help='Password for the admin user (default: admin123)'
        )
        parser.add_argument(
            '--domain',
            default='localhost',
            help='Domain for the public tenant (default: localhost)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up development environment...'))
        
        # Create public tenant
        public_tenant, created = Client.objects.get_or_create(
            schema_name=settings.PUBLIC_SCHEMA_NAME,  # 'public'
            defaults={
                'name': 'Taruvi Public Schema',
                'description': 'Main public schema for Taruvi platform',
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created public tenant: {public_tenant}')
            )
        else:
            self.stdout.write(f'✓ Public tenant already exists: {public_tenant}')
        
        # Create domain
        domain, created = Domain.objects.get_or_create(
            domain=options['domain'],
            defaults={
                'tenant': public_tenant,
                'is_primary': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created domain: {domain}')
            )
        else:
            self.stdout.write(f'✓ Domain already exists: {domain}')
        
        # Create authentication configuration
        auth_config, created = SiteAuthConfig.objects.get_or_create(
            client=public_tenant,
            defaults={
                'allow_email_signup': True,
                'allow_social_login': True,
                'primary_provider': 'email',
                'custom_oauth_settings': {
                    'note': 'Add custom OAuth provider settings here for Keycloak, Okta, etc.'
                }
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created authentication configuration')
            )
        else:
            self.stdout.write('✓ Authentication configuration already exists')
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username=options['admin_username'],
            defaults={
                'email': options['admin_email'],
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if created:
            admin_user.set_password(options['admin_password'])
            admin_user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Created admin user: {admin_user.username} '
                    f'(password: {options["admin_password"]})'
                )
            )
        else:
            self.stdout.write(f'✓ Admin user already exists: {admin_user.username}')
        
        self.stdout.write('\n' + self.style.SUCCESS('Development environment setup complete!'))
        self.stdout.write(f'You can now access:')
        self.stdout.write(f'  • Admin: http://{options["domain"]}:8000/admin/')
        self.stdout.write(f'  • API: http://{options["domain"]}:8000/api/')
        self.stdout.write(f'  • Health: http://{options["domain"]}:8000/health/')
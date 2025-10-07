from django.core.management.base import BaseCommand
from core.models import Client, Domain


class Command(BaseCommand):
    help = 'Create a demo tenant for testing multi-tenant setup'

    def add_arguments(self, parser):
        parser.add_argument('schema_name', type=str, help='Schema name for the tenant')
        parser.add_argument('--name', type=str, help='Display name for the tenant')
        parser.add_argument('--domain', type=str, help='Domain for the tenant (default: {schema_name}.localhost)')

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        tenant_name = options.get('name') or f"{schema_name.title()} Company"
        domain_name = options.get('domain') or f"{schema_name}.localhost"

        # Check if tenant already exists
        if Client.objects.filter(schema_name=schema_name).exists():
            self.stdout.write(
                self.style.WARNING(f'Tenant "{schema_name}" already exists!')
            )
            return

        # Create tenant
        try:
            tenant = Client.objects.create(
                schema_name=schema_name,
                name=tenant_name,
            )
            
            # Create domain
            domain = Domain.objects.create(
                domain=domain_name,
                tenant=tenant,
                is_primary=True
            )

            self.stdout.write(
                self.style.SUCCESS(f'✅ Tenant created successfully!')
            )
            self.stdout.write(f'   Name: {tenant_name}')
            self.stdout.write(f'   Schema: {schema_name}')
            self.stdout.write(f'   Domain: {domain_name}')
            self.stdout.write(f'   URL: http://{domain_name}')
            self.stdout.write('')
            self.stdout.write('🌐 You can now access this tenant at:')
            self.stdout.write(f'   http://{domain_name}')
            self.stdout.write(f'   http://{domain_name}/admin/')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to create tenant: {e}')
            )
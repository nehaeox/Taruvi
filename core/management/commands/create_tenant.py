from django.core.management.base import BaseCommand, CommandError
from core.models import Client, Domain


class Command(BaseCommand):
    help = 'Create a new tenant with domain'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Tenant name')
        parser.add_argument('--schema', required=True, help='Schema name (lowercase, no spaces)')
        parser.add_argument('--domain', required=True, help='Primary domain for the tenant')
        parser.add_argument('--description', help='Optional tenant description')

    def handle(self, *args, **options):
        name = options['name']
        schema_name = options['schema']
        domain_name = options['domain']
        description = options.get('description', '')

        # Validate schema name
        if not schema_name.islower() or ' ' in schema_name:
            raise CommandError('Schema name must be lowercase and contain no spaces')

        # Check if tenant already exists
        if Client.objects.filter(schema_name=schema_name).exists():
            raise CommandError(f'Tenant with schema "{schema_name}" already exists')

        # Check if domain already exists
        if Domain.objects.filter(domain=domain_name).exists():
            raise CommandError(f'Domain "{domain_name}" already exists')

        try:
            # Create tenant
            self.stdout.write(f'Creating tenant: {name} ({schema_name})')
            tenant = Client(
                schema_name=schema_name,
                name=name,
                description=description
            )
            tenant.save()

            # Create domain
            self.stdout.write(f'Creating domain: {domain_name}')
            domain = Domain(
                domain=domain_name,
                tenant=tenant,
                is_primary=True
            )
            domain.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created tenant "{name}" with domain "{domain_name}"'
                )
            )
            self.stdout.write(f'Schema: {schema_name}')
            self.stdout.write(f'Access at: http://{domain_name}:8000/')

        except Exception as e:
            raise CommandError(f'Error creating tenant: {str(e)}')
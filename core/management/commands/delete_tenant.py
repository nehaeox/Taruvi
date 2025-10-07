from django.core.management.base import BaseCommand, CommandError
from core.models import Client, Domain


class Command(BaseCommand):
    help = 'Delete a tenant and its schema'

    def add_arguments(self, parser):
        parser.add_argument('--schema', required=True, help='Schema name to delete')
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompting',
        )

    def handle(self, *args, **options):
        schema_name = options['schema']
        confirm = options['confirm']

        try:
            tenant = Client.objects.get(schema_name=schema_name)
        except Client.DoesNotExist:
            raise CommandError(f'Tenant with schema "{schema_name}" does not exist')

        # Show tenant info
        domains = Domain.objects.filter(tenant=tenant)
        self.stdout.write(f'Tenant: {tenant.name}')
        self.stdout.write(f'Schema: {tenant.schema_name}')
        self.stdout.write(f'Created: {tenant.created_on}')
        
        if domains.exists():
            self.stdout.write('Domains:')
            for domain in domains:
                self.stdout.write(f'  • {domain.domain}')

        # Confirmation
        if not confirm:
            response = input('\nAre you sure you want to delete this tenant? [y/N]: ')
            if response.lower() != 'y':
                self.stdout.write('Operation cancelled')
                return

        try:
            self.stdout.write('Deleting tenant...')
            
            # Delete domains first
            domains.delete()
            
            # Delete tenant (this will drop the schema)
            tenant.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted tenant "{tenant.name}" and its schema'
                )
            )

        except Exception as e:
            raise CommandError(f'Error deleting tenant: {str(e)}')
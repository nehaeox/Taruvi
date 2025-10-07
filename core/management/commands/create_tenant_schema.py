"""
Management command to create tenant schemas safely.
"""

from django.core.management.base import BaseCommand, CommandError
from core.models import Client


class Command(BaseCommand):
    help = 'Create schema for a specific tenant'

    def add_arguments(self, parser):
        parser.add_argument(
            'schema_name',
            type=str,
            help='Schema name of the tenant to create'
        )
        parser.add_argument(
            '--migrate',
            action='store_true',
            help='Run migrations after creating schema'
        )

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        run_migrate = options['migrate']
        
        try:
            client = Client.objects.get(schema_name=schema_name)
        except Client.DoesNotExist:
            raise CommandError(f'Client with schema "{schema_name}" does not exist.')
        
        self.stdout.write(f'Creating schema for tenant: {client.name} ({schema_name})')
        
        try:
            # Create the schema
            client.create_schema(check_if_exists=True)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Schema "{schema_name}" created successfully')
            )
            
            # Run migrations if requested
            if run_migrate:
                from django.core.management import call_command
                self.stdout.write(f'Running migrations for schema: {schema_name}')
                call_command('migrate_schemas', schema_name=schema_name)
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Migrations completed for "{schema_name}"')
                )
                
        except Exception as e:
            raise CommandError(f'Error creating schema: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Tenant schema setup completed for: {client.name}')
        )
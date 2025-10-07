from django.core.management.base import BaseCommand
from core.models import Client, Domain


class Command(BaseCommand):
    help = 'List all tenants and their domains'

    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active tenants',
        )

    def handle(self, *args, **options):
        active_only = options['active_only']
        
        queryset = Client.objects.all()
        if active_only:
            queryset = queryset.filter(is_active=True)
            
        tenants = queryset.order_by('created_on')

        if not tenants.exists():
            self.stdout.write(self.style.WARNING('No tenants found'))
            return

        self.stdout.write(self.style.SUCCESS(f'Found {tenants.count()} tenants:'))
        self.stdout.write('')

        for tenant in tenants:
            # Get domains for this tenant
            domains = Domain.objects.filter(tenant=tenant).order_by('-is_primary')
            
            status = "✓" if tenant.is_active else "✗"
            self.stdout.write(f'{status} {tenant.name} ({tenant.schema_name})')
            self.stdout.write(f'   Created: {tenant.created_on}')
            if tenant.description:
                self.stdout.write(f'   Description: {tenant.description}')
            
            if domains.exists():
                self.stdout.write('   Domains:')
                for domain in domains:
                    primary = " (primary)" if domain.is_primary else ""
                    self.stdout.write(f'     • {domain.domain}{primary}')
            else:
                self.stdout.write('   Domains: None')
            
            self.stdout.write('')
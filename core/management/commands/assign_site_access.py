from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm, remove_perm, get_perms
from core.models import Site, Organization, OrganizationMember


class Command(BaseCommand):
    help = 'Assign or remove site access for organization members'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['grant', 'revoke', 'list'], help='Action to perform')
        parser.add_argument('--user', type=str, help='Username or email')
        parser.add_argument('--site', type=str, help='Site name or schema name')
        parser.add_argument('--organization', type=str, help='Organization name or slug')
        parser.add_argument('--role', choices=['owner', 'member'], help='Grant access to all users with this role')
        parser.add_argument('--permission', choices=['access_site', 'admin_site'], 
                          default='access_site', help='Permission type to grant/revoke')

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'list':
            self.list_site_access(options)
        elif action == 'grant':
            self.grant_access(options)
        elif action == 'revoke':
            self.revoke_access(options)

    def list_site_access(self, options):
        """List site access for users"""
        if options['site']:
            try:
                site = Site.objects.get(name__icontains=options['site'])
            except Site.DoesNotExist:
                try:
                    site = Site.objects.get(schema_name=options['site'])
                except Site.DoesNotExist:
                    raise CommandError(f'Site "{options["site"]}" not found')
            
            self.stdout.write(f'\nUsers with access to site "{site.name}":')
            self.stdout.write('-' * 50)
            
            from guardian.shortcuts import get_users_with_perms
            users_with_perms = get_users_with_perms(site, attach_perms=True)
            
            for user, perms in users_with_perms.items():
                perm_list = ', '.join(perms)
                self.stdout.write(f'{user.username} ({user.email}): {perm_list}')
        
        elif options['user']:
            user = self.get_user(options['user'])
            self.stdout.write(f'\nSites accessible by user "{user.username}":')
            self.stdout.write('-' * 50)
            
            sites = Site.objects.all()
            for site in sites:
                perms = get_perms(user, site)
                if perms:
                    perm_list = ', '.join(perms)
                    self.stdout.write(f'{site.name}: {perm_list}')

    def grant_access(self, options):
        """Grant site access"""
        if not options['site']:
            raise CommandError('--site is required for grant action')
        
        site = self.get_site(options['site'])
        permission = options['permission']
        
        if options['user']:
            # Grant to specific user
            user = self.get_user(options['user'])
            assign_perm(permission, user, site)
            self.stdout.write(
                self.style.SUCCESS(f'Granted {permission} to {user.username} for site {site.name}')
            )
        
        elif options['organization'] and options['role']:
            # Grant to all users with specific role in organization
            org = self.get_organization(options['organization'])
            members = org.members.filter(role=options['role'], is_active=True)
            
            count = 0
            for member in members:
                assign_perm(permission, member.user, site)
                count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Granted {permission} to {count} {options["role"]}s in {org.name} for site {site.name}')
            )
        
        else:
            raise CommandError('Either --user or both --organization and --role are required')

    def revoke_access(self, options):
        """Revoke site access"""
        if not options['site']:
            raise CommandError('--site is required for revoke action')
        
        site = self.get_site(options['site'])
        permission = options['permission']
        
        if options['user']:
            user = self.get_user(options['user'])
            remove_perm(permission, user, site)
            self.stdout.write(
                self.style.SUCCESS(f'Revoked {permission} from {user.username} for site {site.name}')
            )
        
        elif options['organization'] and options['role']:
            org = self.get_organization(options['organization'])
            members = org.members.filter(role=options['role'], is_active=True)
            
            count = 0
            for member in members:
                remove_perm(permission, member.user, site)
                count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Revoked {permission} from {count} {options["role"]}s in {org.name} for site {site.name}')
            )

    def get_user(self, identifier):
        """Get user by username or email"""
        try:
            if '@' in identifier:
                return User.objects.get(email=identifier)
            else:
                return User.objects.get(username=identifier)
        except User.DoesNotExist:
            raise CommandError(f'User "{identifier}" not found')

    def get_site(self, identifier):
        """Get site by name or schema name"""
        try:
            return Site.objects.get(name__icontains=identifier)
        except Site.DoesNotExist:
            try:
                return Site.objects.get(schema_name=identifier)
            except Site.DoesNotExist:
                raise CommandError(f'Site "{identifier}" not found')

    def get_organization(self, identifier):
        """Get organization by name or slug"""
        try:
            return Organization.objects.get(name__icontains=identifier)
        except Organization.DoesNotExist:
            try:
                return Organization.objects.get(slug=identifier)
            except Organization.DoesNotExist:
                raise CommandError(f'Organization "{identifier}" not found')
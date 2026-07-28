from django.core.management.base import BaseCommand
from authentication.models import User


class Command(BaseCommand):
    help = 'Create an admin user for the Vital Hub admin panel'

    def add_arguments(self, parser):
        parser.add_argument('--email',    required=True)
        parser.add_argument('--name',     default='Admin')
        parser.add_argument('--password', required=True)

    def handle(self, *args, **options):
        email = options['email']
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'User {email} already exists — updating role to admin'))
            User.objects.filter(email=email).update(role='admin', is_staff=True)
        else:
            User.objects.create_superuser(
                email=email,
                name=options['name'],
                password=options['password'],
            )
            self.stdout.write(self.style.SUCCESS(f'Admin user created: {email}'))

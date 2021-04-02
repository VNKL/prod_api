from django.core.management.base import BaseCommand

from api.users.models import User


class Command(BaseCommand):
    help = 'init admin'

    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.create_superuser(email='admin@admin.com', username='admin', password='admin')
            admin.is_active = True
            admin.is_superuser = True
            admin.save()

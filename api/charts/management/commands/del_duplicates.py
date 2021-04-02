from django.core.management.base import BaseCommand

from api.charts.utils import del_duplicate_positions


class Command(BaseCommand):
    help = 'start parsing with selected method'

    def handle(self, *args, **options):
        del_duplicate_positions()
        print('duplicates was deleted')

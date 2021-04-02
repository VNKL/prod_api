from django.core.management.base import BaseCommand

from api.charts.serializers import ChartAddSerializer
from api.charts.utils import add_chart


class Command(BaseCommand):
    help = 'start parsing with selected method'

    def add_arguments(self, parser):
        parser.add_argument('-service', action='store', dest='service', type=str)
        parser.add_argument('-date', action='store', dest='date', type=str)

    def handle(self, *args, **options):
        settings = ChartAddSerializer(data=options)
        if settings.is_valid():
            chart = add_chart(**settings.validated_data)
            print(chart)
        else:
            print(settings.errors)

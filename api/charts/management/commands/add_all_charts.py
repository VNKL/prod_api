from django.core.management.base import BaseCommand

from api.charts.serializers import ChartAddAllSerializer
from api.charts.utils import add_chart
from api.settings import CHARTS


class Command(BaseCommand):
    help = 'start parsing with selected method'

    def add_arguments(self, parser):
        parser.add_argument('-date', action='store', dest='date', type=str)

    def handle(self, *args, **options):
        settings = ChartAddAllSerializer(data=options)
        if settings.is_valid():
            msg = add_all_charts(**settings.validated_data)
            print(msg)
        else:
            print(settings.errors)


def add_all_charts(date):
    for service in CHARTS:
        add_chart(service=service, date=date)
    return 'add_all_charts: done'

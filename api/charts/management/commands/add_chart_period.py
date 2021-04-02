from datetime import timedelta
from django.core.management.base import BaseCommand

from api.charts.serializers import ChartAddPeriodSerializer
from .add_chart import add_chart


class Command(BaseCommand):
    help = 'start parsing with selected method'

    def add_arguments(self, parser):
        parser.add_argument('-service', action='store', dest='service', type=str)
        parser.add_argument('-date_from', action='store', dest='date_from', type=str)
        parser.add_argument('-date_to', action='store', dest='date_to', type=str)

    def handle(self, *args, **options):
        settings = ChartAddPeriodSerializer(data=options)
        if settings.is_valid():
            msg = add_chart_period(**settings.validated_data)
            print(msg)
        else:
            print(settings.errors)


def add_chart_period(service, date_from, date_to):
    dates_list = [date_from + timedelta(days=x) for x in range(0, (date_to - date_from).days + 1)]
    for date in dates_list:
        add_chart(service=service, date=date)
    return 'add_chart_period: done'

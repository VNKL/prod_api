from multiprocessing import Process
from django.core.management.base import BaseCommand
from django import db

from api.charts.serializers import ChartAddAllPeriodSerializer
from .add_chart_period import add_chart_period
from api.settings import CHARTS


class Command(BaseCommand):
    help = 'start parsing with selected method'

    def add_arguments(self, parser):
        parser.add_argument('-date_from', action='store', dest='date_from', type=str)
        parser.add_argument('-date_to', action='store', dest='date_to', type=str)

    def handle(self, *args, **options):
        settings = ChartAddAllPeriodSerializer(data=options)
        if settings.is_valid():
            msg = add_all_charts_period(**settings.validated_data)
            print(msg)
        else:
            print(settings.errors)


def add_all_charts_period(date_from, date_to):
    processes = []
    for service in CHARTS:
        pars_params = {'service': service, 'date_from': date_from, 'date_to': date_to}
        db.connections.close_all()
        p = Process(target=add_chart_period, kwargs=pars_params)
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    return 'add_all_charts_period: done'

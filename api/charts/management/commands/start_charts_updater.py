from datetime import datetime, timedelta, time
from django.utils import timezone
from multiprocessing import Process
from time import sleep
from random import uniform

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django import db

from api.charts.utils import del_duplicate_positions
from api.charts.models import Chart


class Command(BaseCommand):
    help = 'start parsing with selected method'

    def handle(self, *args, **options):
        start_updater()


def start_updater():

    last_chart = Chart.objects.filter(service='vk').order_by('-date').first()
    last_date = last_chart.date
    now_date = timezone.now().date()

    if now_date > last_date:
        db.connections.close_all()
        process = Process(target=call_command,
                          args=('add_all_charts_period',),
                          kwargs={'date_from': str(last_date), 'date_to': str(now_date)})
        process.start()
        process.join()
        del_duplicate_positions()

    process = Process(target=_background_updater, args=(now_date,))
    process.start()


def _background_updater(date_from):

    update_time = _get_update_time()

    while True:
        if datetime.now() >= update_time:
            date_to = timezone.now().date()
            db.connections.close_all()
            process = Process(target=call_command,
                              args=('add_all_charts_period',),
                              kwargs={'date_from': str(date_from), 'date_to': str(date_to)})
            process.start()
            process.join()
            del_duplicate_positions()
            date_from = date_to
            update_time = _get_update_time()
        else:
            sleep(uniform(900, 1200))


def _get_update_time():
    return datetime.combine(datetime.now().date(), time(hour=6)) + timedelta(days=1)
from datetime import datetime, timedelta, time
from multiprocessing import Process
from time import sleep
from random import uniform

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django import db


class Command(BaseCommand):
    help = 'start parsing with selected method'

    def handle(self, *args, **options):
        start_resetter()


def start_resetter():
    db.connections.close_all()
    process = Process(target=call_command,
                      args=('reset_accounts',),
                      kwargs={'is_busy': 1, 'is_rate_limited': 1, 'rate_limit_date': 1})
    process.start()
    process.join()

    process = Process(target=_background_resetter)
    process.start()


def _background_resetter():
    update_time = _get_update_time()
    while True:
        if datetime.now() >= update_time:
            db.connections.close_all()
            process = Process(target=call_command,
                              args=('reset_accounts',),
                              kwargs={'is_busy': 1, 'is_rate_limited': 1, 'rate_limit_date': 1})
            process.start()
            process.join()
            print('accounts was reset')
            update_time = _get_update_time()
        else:
            sleep(uniform(30, 60))


def _get_update_time():
    return datetime.now() + timedelta(minutes=5)

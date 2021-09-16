import os
from datetime import datetime, timedelta, time
from django.utils import timezone
from multiprocessing import Process
from time import sleep
from random import uniform

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django import db

from api.parsers.models import Parser


class Command(BaseCommand):
    help = 'delete old parsers'

    def handle(self, *args, **options):
        start_process()


def start_process():
    _delete_old_parsers()
    update_time = _get_update_time()
    while True:
        if datetime.now() >= update_time:
            _delete_old_parsers()
            update_time = _get_update_time()
        else:
            sleep(uniform(900, 1200))


def _get_update_time():
    return datetime.combine(datetime.now().date(), time(hour=1)) + timedelta(days=1)


def _delete_old_parsers():
    db.connections.close_all()
    parsers = Parser.objects.all()
    for parser in parsers:
        now_date = timezone.now()
        if parser.start_date < now_date - timezone.timedelta(days=14):
            zip_path = parser.result_path
            if zip_path:
                os.remove(zip_path)
            parser.delete()
    db.connections.close_all()

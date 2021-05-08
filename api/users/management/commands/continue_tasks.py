from time import sleep
from random import uniform

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django import db

from api.ads.models import Campaign, Automate
from api.parsers.models import Parser
from api.related.models import Scanner
from api.analyzers.models import Analyzer
from api.grabbers.models import Grabber

from multiprocessing import Process


class Command(BaseCommand):
    help = 'continue unfinished tasks after api reload'

    def handle(self, *args, **options):
        continue_tasks()


def continue_tasks():

    campaigns = Campaign.objects.filter(status__in=[4, 5])
    for campaign in campaigns:
        db.connections.close_all()
        process = Process(target=call_command, args=('start_campaign',), kwargs={'campaign_id': campaign.pk})
        process.start()
        sleep(uniform(7, 15))

    automates = Automate.objects.filter(status__in=[1, 2])
    for automate in automates:
        db.connections.close_all()
        process = Process(target=call_command, args=('start_automate',), kwargs={'automate_id': automate.pk})
        process.start()
        sleep(uniform(7, 15))

    parsers = Parser.objects.filter(status__in=[1, 3])
    for parser in parsers:
        db.connections.close_all()
        process = Process(target=call_command, args=('start_parser',), kwargs={'parser_id': parser.pk})
        process.start()
        sleep(uniform(7, 15))

    scanners = Scanner.objects.filter(status__in=[1, 3])
    for scanner in scanners:
        db.connections.close_all()
        process = Process(target=call_command, args=('start_scanner',), kwargs={'scanner_id': scanner.pk})
        process.start()
        sleep(uniform(7, 15))

    analyzers = Analyzer.objects.filter(status__in=[1, 3])
    for analyzer in analyzers:
        db.connections.close_all()
        process = Process(target=call_command, args=('start_analyzer',), kwargs={'analyzer_id': analyzer.pk})
        process.start()
        sleep(uniform(7, 15))

    grabbers = Grabber.objects.filter(status__in=[1, 3])
    for grabber in grabbers:
        db.connections.close_all()
        process = Process(target=call_command, args=('start_grabber',), kwargs={'grabber_id': grabber.pk})
        process.start()
        sleep(uniform(7, 15))

    process = Process(target=call_command, args=('start_charts_updater',))
    process.start()

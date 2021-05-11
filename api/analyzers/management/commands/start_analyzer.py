from random import uniform
from time import sleep
from multiprocessing import Process, Manager

from django.utils import timezone
from django.core.management.base import BaseCommand
from django import db

from api.analyzers.models import Analyzer
from api.analyzers.utils import save_analyzing_result
from vk.artist_analysis.parser import ArtistCardParser
from vk.related.parser import VkRelatedParser


class Command(BaseCommand):
    help = 'start analyzing with selected method'

    def add_arguments(self, parser):
        parser.add_argument('-analyzer_id', action='store', dest='analyzer_id', type=int)

    def handle(self, *args, **options):
        if 'analyzer_id' not in options.keys():
            print('analyzer_id is required to start_analyzer command')
        else:
            start_analyzer(options['analyzer_id'])


def start_analyzer(analyzer_id):

    analyzer = Analyzer.objects.filter(pk=analyzer_id).first()
    if not analyzer:
        print(f'no analyzer with id {analyzer_id}')
    else:
        _start_analyzing(analyzer)


def _do_analyzing_process(analyzer, result_dict):
    db.connections.close_all()
    vk = ArtistCardParser()
    result = vk.get_by_artist_url(artist_card_url=analyzer.param)
    result_dict['result'] = result


def _start_analyzing(analyzer):
    analyzer = _wait_queue(analyzer)
    if not analyzer:
        return

    db.connections.close_all()

    vk = VkRelatedParser()
    artist_name, photo_url = vk.get_artist_card_info(artist_url=analyzer.param)
    if artist_name:
        analyzer.artist_name = artist_name
    if photo_url:
        analyzer.photo_url = photo_url
    analyzer.save()

    db.connections.close_all()
    ticket_manager = Manager()
    result_dict = ticket_manager.dict()
    process = Process(target=_do_analyzing_process, args=(analyzer, result_dict))
    process.start()

    while not _check_stop(process, analyzer):
        sleep(uniform(10, 40))

    if result_dict and 'result' in result_dict.keys():
        result = result_dict['result']
    else:
        result, error = None, 'scanner was stopped or removed'

    analyzer = Analyzer.objects.filter(pk=analyzer.pk).first()
    if analyzer:
        if result:
            save_analyzing_result(analyzer=analyzer, result=result)
        else:
            analyzer.status = 0
            analyzer.error = vk.errors if vk.errors else error
            analyzer.finish_date = timezone.now()
            analyzer.save()


def _check_stop(process, analyzer):
    process.join(timeout=0)
    if not process.is_alive():
        return True

    db.connections.close_all()
    scanner = Analyzer.objects.filter(pk=analyzer.pk).first()
    if not scanner or scanner.status == 0 or scanner.status == 2 or scanner.status == 4:
        process.terminate()
        return True

    return False


def _wait_queue(analyzer):
    earlier_parsers = Analyzer.objects.filter(owner=analyzer.owner, status__in=[1, 3]).exclude(pk=analyzer.pk)
    if earlier_parsers:
        earlier_running = [True for _ in earlier_parsers]
        while any(earlier_running):
            sleep(uniform(5, 15))
            for n, earlier_parser in enumerate(earlier_parsers):
                try:
                    earlier_parser.refresh_from_db()
                    if earlier_parser.status in [0, 2, 4]:
                        earlier_running[n] = False
                except Exception:
                    earlier_running[n] = False

    analyzer = Analyzer.objects.filter(pk=analyzer.pk).first()
    if analyzer:
        analyzer.status = 1
        analyzer.save()
        return analyzer
    else:
        return False

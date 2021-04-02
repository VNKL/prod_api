from django.utils import timezone
from django.core.management.base import BaseCommand

from api.analyzers.models import Analyzer
from api.analyzers.utils import save_analyzing_result
from vk.artist_analysis.parser import ArtistCardParser


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


def _start_analyzing(analyzer):

    vk = ArtistCardParser()
    method = analyzer.method
    error = {'method': analyzer.method,
             'param': analyzer.param,
             'error_msg': f'Error in analyzer {analyzer.pk}'}

    if method == 'get_by_artist_url':
        result = vk.get_by_artist_url(artist_card_url=analyzer.param)

    else:
        result = None

    if result:
        save_analyzing_result(analyzer=analyzer, result=result)

    else:
        analyzer.status = 0
        analyzer.error = vk.errors if vk.errors else error
        analyzer.finish_date = timezone.now()
        analyzer.save()

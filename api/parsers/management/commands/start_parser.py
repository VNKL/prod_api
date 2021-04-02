from time import sleep
from random import uniform

from django.utils import timezone
from django.core.management.base import BaseCommand

from api.parsers.models import Parser, Audio
from api.parsers.serializers import ParserExtendedSerializer, AudioSerializer
from api.parsers.utils import save_parsing_result
from vk.audio_savers.parser import AudioSaversParser


class Command(BaseCommand):
    help = 'start parsing with selected method'

    def add_arguments(self, parser):
        parser.add_argument('-parser_id', action='store', dest='parser_id', type=int)

    def handle(self, *args, **options):
        if 'parser_id' not in options.keys():
            print('parser_id is required to start_parser command')
        else:
            start_parser(options['parser_id'])


def start_parser(parser_id):

    parser = Parser.objects.filter(pk=parser_id).first()
    if not parser:
        print(f'no parser with id {parser_id}')
    else:
        _start_parsing(parser)


def _start_parsing(parser):

    _wait_queue(parser)

    vk = AudioSaversParser()
    method = parser.method
    error = {'method': parser.method,
             'param': parser.param,
             'error_msg': f'Error in parser {parser.pk}'}

    if method == 'get_by_artist_url':
        result = vk.get_by_artist_url(artist_card_url=parser.param, count_only=parser.count_only)

    elif method == 'get_by_track_name':
        result = vk.get_by_track_name(track_name=parser.param, count_only=parser.count_only)

    elif method == 'get_by_group':
        result = vk.get_by_group(group=parser.param, count_only=parser.count_only)

    elif method == 'get_by_playlist':
        result = vk.get_by_playlist(playlist_url=parser.param, count_only=parser.count_only)

    elif method == 'get_by_newsfeed':
        result = vk.get_by_newsfeed(q=parser.param, count_only=parser.count_only)

    elif method == 'get_by_post':
        result = vk.get_by_post(post_url=parser.param, count_only=parser.count_only)

    elif method == 'get_by_chart':
        result = vk.get_by_chart(count_only=parser.count_only)

    elif method == 'get_by_new_releases':
        result = vk.get_by_new_releases(count_only=parser.count_only)

    elif method == 'get_by_parser':
        finded_parser = Parser.objects.filter(owner=parser.owner, pk=parser.param).first()
        if finded_parser:
            data = ParserExtendedSerializer(finded_parser).data
            result = vk.get_by_audios(audio_objects=data['audios'], count_only=parser.count_only, n_threads=10)
        else:
            result = None
            error = {'method': parser.method, 'param': parser.param,
                     'error_msg': f'Error in parser {parser.pk}, not found'}

    elif method == 'get_by_audio':
        finded_audio = Audio.objects.filter(pk=parser.param).first()
        if finded_audio:
            data = AudioSerializer(finded_audio).data
            if isinstance(data['savers'], str):
                data['savers'] = data['savers'].split(',')
                result = [data]
            else:
                result = None
                error = {'method': parser.method, 'param': parser.param,
                         'error_msg': f'Error in parser {parser.pk}, savers not found'}
        else:
            result = None
            error = {'method': parser.method, 'param': parser.param,
                     'error_msg': f'Error in parser {parser.pk}, audio not found'}

    else:
        result = None

    if result:
        save_parsing_result(parser=parser, result=result)

    else:
        parser.status = 0
        parser.error = vk.errors if vk.errors else error
        parser.finish_date = timezone.now()
        parser.save()


def _wait_queue(parser):
    earlier_parsers = Parser.objects.filter(owner=parser.owner, status__in=[1, 3]).exclude(pk=parser.pk)
    if earlier_parsers:
        earlier_running = [True for _ in earlier_parsers]
        while any(earlier_running):
            sleep(uniform(5, 15))
            for n, earlier_parser in enumerate(earlier_parsers):
                earlier_parser.refresh_from_db()
                if earlier_parser.status in [0, 2]:
                    earlier_running[n] = False
    parser.status = 1
    parser.save()

from time import sleep
from random import uniform
from multiprocessing import Process, Manager

from django.utils import timezone
from django.core.management.base import BaseCommand
from django import db

from api.parsers.models import Parser
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
        try:
            _start_parsing(parser)
        except Exception as exc:
            parser.status = 0
            parser.error = str(exc)
            parser.finish_date = timezone.now()
            parser.save()


def _get_parsing_result(function, params, parser):
    db.connections.close_all()
    ticket_manager = Manager()
    result_dict = ticket_manager.dict()
    process = Process(target=_do_parser_process, args=(function, params, result_dict))
    process.start()

    while not _check_stop(process, parser, result_dict):
        sleep(uniform(10, 40))

    if result_dict and 'result' in result_dict.keys() and 'error' in result_dict.keys():
        return result_dict['result'], result_dict['error']
    else:
        return None, 'parser was stopped or removed'


def _check_stop(process, parser, result_dict):
    # process.join(timeout=0)
    # print(process.is_alive())
    # if not process.is_alive():
    #     return True
    if len(result_dict) > 0:
        return True

    db.connections.close_all()
    parser = Parser.objects.filter(pk=parser.pk).first()
    if not parser or parser.status == 0 or parser.status == 2 or parser.status == 4:
        process.terminate()
        return True

    return False


def _do_parser_process(function, params, result_dict):
    result, error = None, None
    # try:
    result = function(**params)
    # except Exception as error:
    #     pass
    result_dict.update({'result': result, 'error': error})


def _start_parsing(parser):

    parser = _wait_queue(parser)
    if not parser:
        return

    db.connections.close_all()
    vk = AudioSaversParser()
    method = parser.method
    params = {'count_only': parser.count_only}
    error = {'method': parser.method,
             'param': parser.param,
             'error_msg': f'Error in parser {parser.pk}'}

    if method == 'get_by_artist_url':
        params['artist_card_url'] = parser.param
        result, error = _get_parsing_result(vk.get_by_artist_url, params, parser)

    elif method == 'get_by_track_name':
        params['track_name'] = parser.param
        result, error = _get_parsing_result(vk.get_by_track_name, params, parser)

    elif method == 'get_by_group':
        params['group'] = parser.param
        result, error = _get_parsing_result(vk.get_by_group, params, parser)

    elif method == 'get_by_playlist':
        params['playlist_url'] = parser.param
        result, error = _get_parsing_result(vk.get_by_playlist, params, parser)

    elif method == 'get_by_newsfeed':
        params['q'] = parser.param
        result, error = _get_parsing_result(vk.get_by_newsfeed, params, parser)

    elif method == 'get_by_post':
        params['post_url'] = parser.param
        result, error = _get_parsing_result(vk.get_by_post, params, parser)

    elif method == 'get_by_chart':
        result, error = _get_parsing_result(vk.get_by_chart, params, parser)

    elif method == 'get_by_new_releases':
        result, error = _get_parsing_result(vk.get_by_new_releases, params, parser)

    else:
        result = None

    parser = Parser.objects.filter(pk=parser.pk).first()
    if parser:
        if result:
            save_parsing_result(parser=parser, result=result)
        else:
            parser.status = 4 if error == 'parser was stopped or removed' else 0
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
                try:
                    earlier_parser.refresh_from_db()
                    if earlier_parser.status in [0, 2, 4]:
                        earlier_running[n] = False
                except Exception:
                    earlier_running[n] = False

    parser = Parser.objects.filter(pk=parser.pk).first()
    if parser:
        parser.status = 1
        parser.save()
        return parser
    else:
        return False

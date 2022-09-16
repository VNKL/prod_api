from random import uniform
from time import sleep
from multiprocessing import Process, Manager

from django.utils import timezone
from django.core.management.base import BaseCommand
from django import db

from api.users_audios.models import Parser, Item
from vk.users_audios.parser import UserAudiosParser


class Command(BaseCommand):
    help = 'start parsing users audios'

    def add_arguments(self, parser):
        parser.add_argument('-parser_id', action='store', dest='parser_id', type=int)

    def handle(self, *args, **options):
        if 'parser_id' not in options.keys():
            print('parser_id is required to start_users_audios_parser command')
        else:
            start_parser(options['parser_id'])


def start_parser(parser_id):

    parser = Parser.objects.filter(pk=parser_id).first()
    if not parser:
        print(f'no users audios parser with id {parser_id}')
    else:
        try:
            _start_parsing(parser)
        except Exception as exc:
            parser.status = 0
            parser.error = str(exc)
            parser.finish_date = timezone.now()
            parser.save()


def _do_parsing_process(parser, result_dict):
    db.connections.close_all()
    vk = UserAudiosParser()
    user_ids = _get_user_ids(parser)
    result = vk.get(user_ids=user_ids, n_last=parser.n_last, get_type=parser.type)
    result_dict['result'] = result


def _get_user_ids(parser):
    user_ids = parser.user_ids
    if not user_ids:
        return []

    if ', ' in user_ids:
        user_ids = user_ids.split(', ')
    if ',' in user_ids:
        user_ids = user_ids.split(',')
    elif '\n' in user_ids:
        user_ids = user_ids.split('\n')
    else:
        try:
            user_ids = [int(user_ids)]
        except ValueError:
            return []

    int_ids = []
    for x in user_ids:
        try:
            int_ids.append(int(x))
        except ValueError:
            continue

    return int_ids


def _check_stop(process, parser):
    process.join(timeout=0)
    if not process.is_alive():
        return True

    db.connections.close_all()
    parser = Parser.objects.filter(pk=parser.pk).first()
    if not parser or parser.status == 0 or parser.status == 2 or parser.status == 4:
        process.terminate()
        return True

    return False


def _start_parsing(parser):
    parser = _wait_queue(parser)
    if not parser:
        return

    db.connections.close_all()
    ticket_manager = Manager()
    result_dict = ticket_manager.dict()
    process = Process(target=_do_parsing_process, args=(parser, result_dict))
    process.start()

    while not _check_stop(process, parser):
        sleep(uniform(10, 40))

    if result_dict and 'result' in result_dict.keys():
        result = result_dict['result']
    else:
        result, error = None, 'scanner was stopped or removed'

    parser = Parser.objects.filter(pk=parser.pk).first()
    if parser:
        if result:
            save_parsing_result(parser=parser, result=result)
        else:
            parser.status = 0
            parser.finish_date = timezone.now()
            parser.save()


def save_parsing_result(parser, result):
    parser.finish_date = timezone.now()
    parser.status = 2

    if result:
        _save_items(parser, result)

    parser.save()


def _save_items(parser, items):
    item_objs = []
    for item in items:
        item_obj = Item(parser=parser,
                        name=item['item'],
                        share_users=item['share_users'],
                        share_items=item['share_items'])
        item_objs.append(item_obj)

    Item.objects.bulk_create(item_objs, batch_size=40)


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

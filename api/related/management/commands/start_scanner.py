from random import uniform
from time import sleep
from multiprocessing import Process, Manager

from django.utils import timezone
from django.core.management.base import BaseCommand
from django import db

from api.related.models import Scanner, Artist
from vk.related.parser import VkRelatedParser


class Command(BaseCommand):
    help = 'start scanning related'

    def add_arguments(self, parser):
        parser.add_argument('-scanner_id', action='store', dest='scanner_id', type=int)

    def handle(self, *args, **options):
        if 'scanner_id' not in options.keys():
            print('scanner_id is required to start_scanner command')
        else:
            start_scanner(options['scanner_id'])


def start_scanner(scanner_id):

    scanner = Scanner.objects.filter(pk=scanner_id).first()
    if not scanner:
        print(f'no scanner with id {scanner_id}')
    else:
        try:
            _start_scanning(scanner)
        except Exception as exc:
            scanner.status = 0
            scanner.error = str(exc)
            scanner.finish_date = timezone.now()
            scanner.save()


def _do_scanning_process(scanner, result_dict):
    vk = VkRelatedParser()
    result = vk.get_related_artists(artist_url=scanner.artist_url,
                                    listens_min=scanner.listens_min,
                                    listens_max=scanner.listens_max,
                                    n_releases=scanner.n_releases,
                                    last_days=scanner.last_days,
                                    median_days=scanner.median_days,
                                    max_recurse=scanner.recurse)
    result_dict['result'] = result


def _check_stop(process, scanner):
    process.join(timeout=0)
    if not process.is_alive():
        return True

    db.connections.close_all()
    scanner = Scanner.objects.filter(pk=scanner.pk).first()
    if not scanner or scanner.status == 0 or scanner.status == 2 or scanner.status == 4:
        process.terminate()
        return True

    return False


def _start_scanning(scanner):
    scanner = _wait_queue(scanner)
    if not scanner:
        return

    db.connections.close_all()

    vk = VkRelatedParser()
    error = {'error_msg': f'Error in scanner {scanner.pk}'}

    artist_name, photo_url = vk.get_artist_card_info(artist_url=scanner.artist_url)
    if artist_name:
        scanner.artist_name = artist_name
    if photo_url:
        scanner.photo_url = photo_url
    scanner.save()

    ticket_manager = Manager()
    result_dict = ticket_manager.dict()
    process = Process(target=_do_scanning_process, args=(scanner, result_dict))
    process.start()

    while not _check_stop(process, scanner):
        sleep(uniform(10, 40))

    if result_dict and 'result' in result_dict.keys():
        result = result_dict['result']
    else:
        result, error = None, 'scanner was stopped or removed'

    scanner = Scanner.objects.filter(pk=scanner.pk).first()
    if scanner:
        if result:
            save_scanning_result(scanner=scanner, result=result)
        else:
            scanner.status = 0
            scanner.error = vk.errors if vk.errors else error
            scanner.finish_date = timezone.now()
            scanner.save()


def save_scanning_result(scanner, result):
    artists = result['related']

    scanner.artist_name = result['artist_name'] or None
    scanner.photo_url = result['photo_url'] or None
    scanner.related_count = len(artists) or 0
    scanner.finish_date = timezone.now()
    scanner.status = 2

    if artists:
        _save_artists(scanner, artists)

    scanner.save()


def _save_artists(scanner, artists):
    for artist in artists:
        group_name, group_url, user_name, user_url = _pars_links(artist['links'])
        card_url = f"https://vk.com/artist/{artist['domain']}"
        artist_obj = Artist.objects.filter(card_url=card_url).first()
        if not artist_obj:
            artist_obj = Artist.objects.create()

        artist_obj.scanners.add(scanner)
        artist_obj.name = artist['name']
        artist_obj.card_url = card_url
        artist_obj.group_name = group_name
        artist_obj.group_url = group_url
        artist_obj.user_name = user_name
        artist_obj.user_url = user_url
        artist_obj.save()


def _pars_links(links):
    group_name, group_url, user_name, user_url = None, None, None, None
    for link in links:
        if 'meta' in link.keys() and link['meta']:
            if 'content_type' in link['meta'].keys():
                if link['meta']['content_type'] == 'group':
                    group_name = f"{link['title']} ({link['subtitle']})"
                    group_url = link['url']
                elif link['meta']['content_type'] == 'user':
                    user_name = f"{link['title']} ({link['subtitle']})"
                    user_url = link['url']
    return group_name, group_url, user_name, user_url


def _wait_queue(scanner):
    earlier_parsers = Scanner.objects.filter(owner=scanner.owner, status__in=[1, 3]).exclude(pk=scanner.pk)
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

    scanner = Scanner.objects.filter(pk=scanner.pk).first()
    if scanner:
        scanner.status = 1
        scanner.save()
        return scanner
    else:
        return False

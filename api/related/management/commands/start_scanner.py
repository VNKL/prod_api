from django.utils import timezone
from django.core.management.base import BaseCommand

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
        _start_scanning(scanner)


def _start_scanning(scanner):

    vk = VkRelatedParser()
    error = {'error_msg': f'Error in scanner {scanner.pk}'}

    result = vk.get_related_artists(artist_url=scanner.artist_url,
                                    listens=scanner.listens,
                                    n_releases=scanner.n_releases,
                                    last_days=scanner.last_days,
                                    median_days=scanner.median_days,
                                    max_recurse=scanner.recurse)

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

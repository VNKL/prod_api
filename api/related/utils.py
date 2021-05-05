from django.utils import timezone

from .models import Scanner


def create_scanner(user, data):
    scanner = Scanner(owner=user,
                      status=3,
                      start_date=timezone.now(),
                      artist_url=data['url'],
                      listens_min=data['listens_min'],
                      listens_max=data['listens_max'],
                      n_releases=data['n_releases'],
                      last_days=data['last_days'],
                      median_days=data['median_days'],
                      recurse=data['recurse'])
    scanner.save()
    return {'scanner_id': scanner.pk}


def delete_scanner(user, data):
    scanner = Scanner.objects.filter(owner=user, pk=data['id']).first()
    if not scanner:
        return {'error': f'not found or no permissions to scanner with id {data["id"]}'}

    scanner.delete()
    return {'response': f"scanner with id {data['id']} was deleted"}


def related_results_to_csv_filename(scanner):
    return f"{scanner['artist_name']}.csv"


def related_results_to_filebody(scanner):
    header = 'Артист\tКарточка артиста\tПаблик артиста\tСсылка на паблик\tЛичная страница артиста\tСсылка на страницу\n'
    if 'artists' in scanner.keys():
        for artist in scanner['artists']:
            header += f"{artist['name']}\t" \
                      f"{artist['card_url']}\t" \
                      f"{artist['group_name'] or '-'}\t" \
                      f"{artist['group_url'] or '-'}\t" \
                      f"{artist['user_name'] or '-'}\t" \
                      f"{artist['user_url'] or '-'}\n"
    return header

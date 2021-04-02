from django.utils import timezone

from .models import Scanner


def create_scanner(user, data):
    scanner = Scanner(owner=user,
                      status=1,
                      start_date=timezone.now(),
                      artist_url=data['url'],
                      listens=data['listens'],
                      n_releases=data['n_releases'],
                      last_days=data['last_days'],
                      median_days=data['median_days'],
                      recurse=data['recurse'])
    scanner.save()
    return {'scanner_id': scanner.pk}

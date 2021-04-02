from django.utils import timezone

from .models import Grabber


def create_grabber(user, data):
    grabber = Grabber(owner=user,
                      status=1,
                      group=data['group'],
                      with_audio=data['with_audio'],
                      ads_only=data['ads_only'],
                      with_ads=data['with_ads'],
                      date_from=data['date_from'] if 'date_from' in data.keys() else None,
                      date_to=data['date_to'] if 'date_to' in data.keys() else None,
                      start_date=timezone.now())
    grabber.save()
    return {'grabber_id': grabber.pk}

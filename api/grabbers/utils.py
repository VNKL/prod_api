from django.utils import timezone

from .models import Grabber, Post, Playlist, Audio


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


def delete_grabber(user, data):
    grabber = Grabber.objects.filter(owner=user, pk=data['id']).first()
    if not grabber:
        return {'error': f'not found or no permissions to grabber with id {data["id"]}'}

    posts = Post.objects.filter(grabbers=grabber)
    if posts:
        Playlist.objects.filter(posts__in=posts).delete()
        Audio.objects.filter(posts__in=posts).delete()
        Post.objects.filter(grabbers=grabber).delete()

    grabber.delete()
    return {'response': f"grabber with id {data['id']} was deleted"}


def grabber_results_to_csv_filename(grabber):
    return f"{grabber['group_name']} ({grabber['finish_date']})"


def grabber_results_to_filebody(grabber):
    header = 'Пост\tРекламный\tЕсть аудио\tЕсть плейлист\tПрослушивания\tДобавления\tДубли аудио\t' \
             'Лайки\tРепосты\tКомменты\tДата и время поста\n'

    for post in grabber['posts']:
        followers = sum([x['followers'] for x in post['playlists']])
        saves = sum(x['savers_count'] for x in post['audios'])
        header += f"https://vk.com/wall{post['owner_id']}_{post['post_id']}\t" \
                  f"{'Да' if post['is_ad'] else 'Нет'}\t" \
                  f"{'Да' if post['has_audios'] else 'Нет'}\t" \
                  f"{'Да' if post['has_playlist'] else 'Нет'}\t" \
                  f"{sum([x['listens'] for x in post['playlists']])}\t" \
                  f"{followers + saves}\t" \
                  f"{sum(x['doubles'] for x in post['audios'])}\t" \
                  f"{post['likes']}\t" \
                  f"{post['reposts']}\t" \
                  f"{post['comments']}\t" \
                  f"{str(post['date']).split('+')[0].replace('T', ', ')}\n"

    return header

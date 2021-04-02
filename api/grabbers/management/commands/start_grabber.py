from collections import Counter
from datetime import datetime

from django.utils import timezone
from django.core.management.base import BaseCommand

from api.grabbers.models import Grabber, Post, Playlist, Audio
from vk.wall_grabbing.parser import WallParser


class Command(BaseCommand):
    help = 'start grabbing with selected method'

    def add_arguments(self, parser):
        parser.add_argument('-grabber_id', action='store', dest='grabber_id', type=int)

    def handle(self, *args, **options):
        if 'grabber_id' not in options.keys():
            print('grabber_id is required to start_grabber command')
        else:
            start_grabber(options['grabber_id'])


def start_grabber(grabber_id):

    grabber = Grabber.objects.filter(pk=grabber_id).first()
    if not grabber:
        print(f'no grabber with id {grabber_id}')
    else:
        _start_grabbing(grabber)


def _start_grabbing(grabber):

    vk = WallParser()
    error = {'error_msg': f'Error in grabber {grabber.pk}'}

    result = vk.get_group_posts(group=grabber.group,
                                date_from=grabber.date_from,
                                date_to=grabber.date_to,
                                with_audio=grabber.with_audio,
                                with_dark_posts=grabber.with_ads,
                                dark_posts_only=grabber.ads_only)
    if result:
        save_grabbing_result(grabber=grabber, result=result)
    elif not result and isinstance(result, list):
        grabber.status = 2
        grabber.posts_count = 0
        grabber.finish_date = timezone.now()
        grabber.save()
    else:
        grabber.status = 0
        grabber.error = vk.errors if vk.errors else error
        grabber.finish_date = timezone.now()
        grabber.save()


def save_grabbing_result(grabber, result):
    audios_counter = _calculate_audio_doubles(result)

    for post in result:
        playlists, audios = False, False
        if 'attachments' in post.keys():
            playlists = [x['playlist'] for x in post['attachments'] if x['type'] == 'playlist']
            audios = [x['audio'] for x in post['attachments'] if x['type'] == 'audio']
            audios = _mark_audio_dounles(audios, audios_counter)

        post_obj = _save_post_obj(audios, grabber, playlists, post)

        if playlists:
            _save_playlist_objs(playlists, post_obj)

        if audios:
            _save_audio_objs(audios, post_obj)

    grabber.posts_count = len(result)
    grabber.status = 2
    grabber.finish_date = timezone.now()
    grabber.save()


def _calculate_audio_doubles(posts):
    all_audios = []
    for post in posts:
        if 'attachments' in post.keys():
            audios = [x['audio'] for x in post['attachments'] if x['type'] == 'audio']
            all_audios.extend(audios)

    audio_ids = [f"{x['owner_id']}_{x['id']}" for x in all_audios]
    return Counter(audio_ids)


def _mark_audio_dounles(audios, counter):
    marked_audios = []
    for audio in audios:
        audio_id = f"{audio['owner_id']}_{audio['id']}"
        doubles = counter[audio_id] - 1
        audio = audio.copy()
        audio['doubles'] = doubles
        marked_audios.append(audio)
    return marked_audios


def _save_audio_objs(audios, post_obj):
    for audio in audios:
        au_existed = Audio.objects.filter(owner_id=audio['owner_id'], audio_id=audio['id']).first()
        if au_existed:
            au_existed.posts.add(post_obj)
            au_existed.savers_count = audio['savers_count']
            au_existed.doubles = audio['doubles']
            au_existed.parsing_date = timezone.now()
            au_existed.save()
        else:
            au_title = audio['title']
            if 'subtitle' in audio.keys():
                au_title += f" ({audio['subtitle']})"
            au_obj = Audio.objects.create(owner_id=audio['owner_id'],
                                          audio_id=audio['id'],
                                          artist=audio['artist'],
                                          title=au_title,
                                          savers_count=audio['savers_count'],
                                          doubles=audio['doubles'],
                                          date=datetime.fromtimestamp(audio['date']),
                                          parsing_date=timezone.now(),
                                          source='playlist' if 'source' in audio.keys() else 'post')
            au_obj.posts.add(post_obj)


def _save_playlist_objs(playlists, post_obj):
    for playlist in playlists:
        pl_existed = Playlist.objects.filter(owner_id=playlist['owner_id'], playlist_id=playlist['id']).first()
        if pl_existed:
            pl_existed.posts.add(post_obj)
            pl_existed.listens = playlist['listens']
            pl_existed.followers = playlist['followers']
            pl_existed.update_date = datetime.fromtimestamp(playlist['update_time'])
            pl_existed.parsing_date = timezone.now()
            pl_existed.save()
        else:
            pl_obj = Playlist.objects.create(owner_id=playlist['owner_id'],
                                             playlist_id=playlist['id'],
                                             access_hash=playlist['access_hash'],
                                             listens=playlist['listens'],
                                             followers=playlist['followers'],
                                             title=playlist['title'],
                                             create_date=datetime.fromtimestamp(playlist['create_time']),
                                             update_date=datetime.fromtimestamp(playlist['update_time']),
                                             parsing_date=timezone.now())
            pl_obj.posts.add(post_obj)


def _save_post_obj(audios, grabber, playlists, post):
    post_existed = Post.objects.filter(owner_id=post['owner_id'], post_id=post['id']).first()
    if post_existed:
        post_existed.grabbers.add(grabber)
        return post_existed

    post_obj = Post.objects.create(owner_id=post['owner_id'],
                                   post_id=post['id'],
                                   is_ad=True if post['post_type'] == 'post_ads' else False,
                                   likes=post['likes']['count'],
                                   reposts=post['reposts']['count'],
                                   comments=post['comments']['count'] if 'comments' in post.keys() else 0,
                                   text=post['text'] if 'text' in post.keys() else None,
                                   has_playlist=True if playlists else False,
                                   has_audios=True if audios else False,
                                   date=datetime.fromtimestamp(post['date']))
    post_obj.grabbers.add(grabber)
    return post_obj

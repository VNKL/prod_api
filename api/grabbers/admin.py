from django.contrib import admin

from .models import Grabber, Post, Playlist, Audio


@admin.register(Grabber)
class GrabberAdmin(admin.ModelAdmin):
    list_display = 'id', 'owner', 'status', 'error', 'group', 'with_audio', 'ads_only', 'with_ads', \
                   'date_from', 'date_to', 'posts_count', 'start_date', 'finish_date'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = 'id', 'owner_id', 'post_id', 'is_ad', 'likes', 'reposts', 'comments', \
                   'has_playlist', 'has_audios', 'date'


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = 'id', 'title', 'listens', 'followers', 'owner_id', 'playlist_id', 'access_hash', \
                   'create_date', 'update_date', 'parsing_date'


@admin.register(Audio)
class AudioAdmin(admin.ModelAdmin):
    list_display = 'id', 'artist', 'title', 'savers_count', 'doubles', 'source', 'owner_id', 'audio_id', \
                   'date', 'parsing_date'

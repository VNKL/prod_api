from django.contrib import admin

from .models import Campaign, Ad, Playlist, Audio, Automate


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = 'id', 'owner', 'cabinet_name', 'client_name', 'artist', 'title', 'status', 'errors', 'is_automate', \
                   'spent', 'reach', 'listens', 'saves', 'create_date', 'update_date', 'audience_count'


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = 'id', 'campaign', 'ad_name', 'status', 'approved', 'spent', 'reach', 'cpm', \
                   'listens', 'cpl', 'lr', 'saves', 'cps', 'sr', 'cpm_price', 'audience_count'


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = 'id', 'ad', 'title', 'listens', 'followers', 'owner_id', 'playlist_id', 'access_key'


@admin.register(Audio)
class AudioAdmin(admin.ModelAdmin):
    list_display = 'id', 'ad', 'artist', 'title', 'savers_count', 'owner_id', 'audio_id'


@admin.register(Automate)
class AutomateAdmin(admin.ModelAdmin):
    list_display = 'id', 'campaign', 'type', 'max_cpm', 'status', 'error', 'start', 'finish', \
                   'create_date', 'finish_date'

from django.contrib import admin

from api.related.models import Artist, Scanner


@admin.register(Scanner)
class ScannerAdmin(admin.ModelAdmin):
    list_display = 'id', 'owner', 'artist_url', 'status', 'error', 'artist_name', 'related_count', 'listens', \
                   'n_releases', 'last_days', 'median_days', 'recurse', 'start_date', 'finish_date'


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = 'id', 'name', 'card_url', 'group_name', 'group_url', 'user_name', 'user_url'

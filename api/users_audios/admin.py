from django.contrib import admin

from api.users_audios.models import Parser, Item


@admin.register(Parser)
class ParserAdmin(admin.ModelAdmin):
    list_display = 'id', 'owner', 'name', 'status', 'error', 'n_last', 'type', 'start_date', 'finish_date'


@admin.register(Item)
class ArtistAdmin(admin.ModelAdmin):
    list_display = 'id', 'name', 'share_users', 'share_items'

from django.contrib import admin

from .models import Parser, Audio


@admin.register(Parser)
class ParserAdmin(admin.ModelAdmin):
    list_display = 'id', 'owner', 'method', 'param', 'count_only', 'status', 'error', 'audios_count', 'savers_count', \
                   'start_date', 'finish_date'


@admin.register(Audio)
class AudioAdmin(admin.ModelAdmin):
    list_display = 'id', 'artist', 'title', 'savers_count', 'source', 'doubles', 'date', 'parsing_date'


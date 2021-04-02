from django.contrib import admin

from .models import Chart, Position, Track
from .serializers import TrackSerializer


@admin.register(Chart)
class ChartAdmin(admin.ModelAdmin):
    list_display = 'id', 'date', 'service'


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = 'id', 'get_track_name', 'service', 'current', 'previous', 'delta', 'date'

    def get_track_name(self, instance):
        track = Track.objects.filter(positions=instance).first()
        track = TrackSerializer(track).data
        return f"{track['artist']} - {track['title']}"


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = 'id', 'artist', 'title'

from rest_framework import serializers

from .models import Scanner, Artist


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = 'id', 'name', 'card_url', 'group_name', 'group_url', 'user_name', 'user_url'


class ScannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scanner
        fields = 'id', 'artist_url', 'artist_name', 'related_count', 'photo_url', 'listens', 'n_releases', \
                 'last_days', 'median_days', 'recurse', 'start_date', 'finish_date'


class ScannerExtendedSerializer(serializers.ModelSerializer):
    artists = serializers.SerializerMethodField()

    def get_artists(self, instance):
        ordered_queryset = Artist.objects.filter(scanners=instance).order_by('name')
        return ArtistSerializer(ordered_queryset, many=True, context=self.context).data

    class Meta:
        model = Scanner
        fields = 'id', 'artist_url', 'artist_name', 'related_count', 'photo_url', 'listens', 'n_releases', \
                 'last_days', 'median_days', 'recurse', 'start_date', 'finish_date', 'artists'


class CreateScannerSerializer(serializers.Serializer):
    url = serializers.CharField()
    listens = serializers.IntegerField()
    n_releases = serializers.IntegerField()
    last_days = serializers.IntegerField()
    median_days = serializers.IntegerField()
    recurse = serializers.IntegerField()


class GetScannerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    extended = serializers.BooleanField(default=False)

from rest_framework import serializers

from .models import Audio, Parser


class AudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audio
        fields = 'id', 'artist', 'title', 'savers_count', 'source', 'doubles', 'date', 'parsing_date', \
                 'owner_id', 'audio_id', 'post_owner_id', 'post_id', 'chart_position'


class AudioGetSerializer(serializers.Serializer):
    owner_id = serializers.IntegerField()
    audio_id = serializers.IntegerField()


class AudioSearchSerializer(serializers.Serializer):
    artist = serializers.CharField(max_length=100)
    title = serializers.CharField(max_length=100)


class ParserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parser
        fields = 'id', 'method', 'param', 'count_only', 'status', 'error', \
                 'savers_count', 'audios_count', 'result_path', 'start_date', 'finish_date'


class ParserExtendedSerializer(serializers.ModelSerializer):
    audios = serializers.SerializerMethodField()

    def get_audios(self, instance):
        ordered_queryset = Audio.objects.filter(parser=instance).order_by('-savers_count')
        return AudioSerializer(ordered_queryset, many=True, context=self.context).data

    class Meta:
        model = Parser
        fields = 'id', 'owner', 'status', 'error', 'method', 'param', 'count_only', 'start_date', 'finish_date', \
                 'savers_count', 'audios_count', 'result_path', 'audios'


class ParserAddSerializer(serializers.Serializer):
    artist_url = serializers.CharField(max_length=100, allow_blank=True, required=False)
    track_name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    group = serializers.CharField(max_length=100, allow_blank=True, required=False)
    playlist = serializers.CharField(max_length=100, allow_blank=True, required=False)
    post = serializers.CharField(max_length=100, allow_blank=True, required=False)
    newsfeed = serializers.CharField(max_length=100, required=False)
    chart = serializers.BooleanField(required=False)
    new_releases = serializers.BooleanField(required=False)
    count_only = serializers.BooleanField(default=True)
    parser = serializers.IntegerField(required=False)
    audio = serializers.IntegerField(required=False)


class ParserGetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    extended = serializers.BooleanField(default=False)


class ParserDownloadSerializer(serializers.Serializer):
    id = serializers.IntegerField()

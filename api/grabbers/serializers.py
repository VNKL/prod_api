from rest_framework import serializers

from .models import Grabber, Post, Playlist, Audio


class AudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audio
        fields = 'id', 'artist', 'title', 'savers_count', 'doubles', 'source', 'date', 'parsing_date', \
                 'owner_id', 'audio_id'


class PlaylistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Playlist
        fields = 'id', 'title', 'listens', 'followers', 'owner_id', 'playlist_id', 'access_hash', \
                 'create_date', 'update_date', 'parsing_date'


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = 'id', 'owner_id', 'post_id', 'likes', 'reposts', 'comments', \
                 'has_playlist', 'has_audios', 'is_ad', 'date'


class PostExtendedSerializer(serializers.ModelSerializer):
    audios = AudioSerializer(many=True)
    playlists = PlaylistSerializer(many=True)

    class Meta:
        model = Post
        fields = 'id', 'owner_id', 'post_id', 'likes', 'reposts', 'comments', \
                 'has_playlist', 'has_audios', 'is_ad', 'date', 'text', 'playlists', 'audios'


class GrabberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grabber
        fields = '__all__'


class GrabberExtendedSerializer(serializers.ModelSerializer):
    posts = serializers.SerializerMethodField()

    def get_posts(self, instance):
        ordered_queryset = Post.objects.filter(grabbers=instance).order_by('-date')
        return PostExtendedSerializer(ordered_queryset, many=True, context=self.context).data

    class Meta:
        model = Grabber
        fields = 'id', 'owner', 'group', 'group_name', 'group_ava', 'status', 'error', \
                 'with_audio', 'ads_only', 'with_ads', 'date_from', 'date_to', 'start_date', 'finish_date', \
                 'posts_count', 'posts'


class GrabberAddSerializer(serializers.Serializer):
    group = serializers.CharField(max_length=100)
    with_audio = serializers.BooleanField(default=True)
    ads_only = serializers.BooleanField(default=False)
    with_ads = serializers.BooleanField(default=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class GrabberGetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    extended = serializers.BooleanField(default=False)
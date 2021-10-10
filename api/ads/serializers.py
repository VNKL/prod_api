from rest_framework import serializers

from .models import Campaign, Ad, Playlist, Audio, Automate


class AudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audio
        fields = 'id', 'artist', 'title', 'savers_count', 'owner_id', 'audio_id'


class PlaylistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Playlist
        fields = 'id', 'title', 'listens', 'followers', 'owner_id', 'playlist_id', 'access_hash'


class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        fields = 'id', 'ad_id', 'ad_name', 'status', 'approved', 'post_owner', 'post_id', \
                 'spent', 'reach', 'cpm', 'listens', 'cpl', 'lr', 'saves', 'cps', 'sr', \
                 'clicks', 'cpc', 'cr', 'joins', 'cpj', 'jr', 'audience_count'


class AdExtendedSerializer(serializers.ModelSerializer):
    audios = AudioSerializer(many=True)
    playlist = PlaylistSerializer()

    class Meta:
        model = Ad
        fields = 'id', 'ad_id', 'ad_name', 'status', 'approved', 'post_owner', 'post_id', \
                 'spent', 'reach', 'cpm', 'listens', 'cpl', 'lr', 'saves', 'cps', 'sr', \
                 'clicks', 'cpc', 'cr', 'joins', 'cpj', 'jr', 'audience_count', \
                 'playlist', 'audios'


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = 'id', 'campaign_name', 'artist', 'title', 'cover_url', 'campaign_id', \
                 'status', 'is_automate', 'has_moderate_audios', 'audios_is_moderated', \
                 'spent', 'reach', 'cpm', 'listens', 'cpl', 'lr', 'saves', 'cps', 'sr', \
                 'clicks', 'cpc', 'cr', 'joins', 'cpj', 'jr', 'audience_count', \
                 'create_date', 'update_date'


class CampaignExtendedSerializer(serializers.ModelSerializer):
    ads = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = 'id', 'campaign_name', 'artist', 'title', 'cover_url', \
                 'campaign_id', 'cabinet_id', 'client_id', 'group_id', 'fake_group_id', \
                 'status', 'is_automate', 'has_moderate_audios', 'audios_is_moderated', \
                 'spent', 'reach', 'cpm', 'listens', 'cpl', 'lr', 'saves', 'cps', 'sr', \
                 'clicks', 'cpc', 'cr', 'joins', 'cpj', 'jr', 'audience_count', \
                 'create_date', 'update_date', 'ads'

    def get_ads(self, instance):
        ads = instance.ads.all().order_by('-pk')
        return AdSerializer(ads, many=True).data


class CreateCampaignSerializer(serializers.Serializer):
    cabinet_id = serializers.IntegerField()
    client_id = serializers.IntegerField(required=False)
    group_id = serializers.IntegerField()
    reference_url = serializers.CharField()
    money_limit = serializers.IntegerField()
    sex = serializers.CharField(required=False)
    music = serializers.BooleanField(default=False)
    boom = serializers.BooleanField(default=False)
    age_disclaimer = serializers.IntegerField(default=5)
    age_from = serializers.IntegerField(default=0)
    age_to = serializers.IntegerField(default=0)
    musicians = serializers.CharField(required=False)
    groups = serializers.CharField(required=False)
    related = serializers.BooleanField(default=False)
    retarget = serializers.CharField(required=False)
    empty_ads = serializers.IntegerField(default=0)
    retarget_exclude = serializers.CharField(required=False)
    retarget_save_seen = serializers.CharField(required=False)
    retarget_save_positive = serializers.CharField(required=False)
    retarget_save_negative = serializers.CharField(required=False)


class GetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    extended = serializers.BooleanField(default=False)


class AutomateExtendedSerializer(serializers.ModelSerializer):
    campaign = CampaignExtendedSerializer()

    class Meta:
        model = Automate
        fields = 'id', 'status', 'type', 'target_cost', 'start', 'finish', 'create_date', 'finish_date', 'campaign'


class AutomateSerializer(serializers.ModelSerializer):
    campaign = CampaignSerializer()

    class Meta:
        model = Automate
        fields = 'id', 'status', 'type', 'target_cost', 'start', 'finish', 'create_date', 'finish_date', 'campaign'


class CreateAutomateSerializer(serializers.Serializer):
    campaign_id = serializers.IntegerField()
    target_cost = serializers.FloatField()
    type = serializers.IntegerField()
    start = serializers.IntegerField(default=0)
    finish = serializers.IntegerField(default=0)


class StopAutomateSerializer(serializers.Serializer):
    id = serializers.IntegerField()


class GetRetargetSerializer(serializers.Serializer):
    cabinet_id = serializers.IntegerField()
    client_id = serializers.IntegerField(required=False)

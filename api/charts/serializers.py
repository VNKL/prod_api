from rest_framework import serializers

from .models import Chart, Position, Track
from api.settings import CHARTS


class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = 'id', 'artist', 'title', 'has_cover', 'cover_url', 'has_distributor', 'distributor'


class PositionForTrackForSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = 'service', 'date', 'current', 'previous', 'delta'


class TrackForSearchSerializer(serializers.ModelSerializer):
    positions_count = serializers.SerializerMethodField()
    max_position_delta = serializers.SerializerMethodField()

    def _get_positions(self, instance):
        filter_params = {'track': instance}
        if 'service' in self.context.keys():
            filter_params['service'] = self.context['service']
        if 'deltas' in self.context.keys():
            filter_params['delta__isnull'] = False
        if 'dates' in self.context.keys():
            filter_params['date__in'] = self.context['dates']
        return Position.objects.filter(**filter_params)

    def get_positions_count(self, instance):
        positions = self._get_positions(instance)
        return positions.count()

    def get_max_position_delta(self, instance):
        positions = self._get_positions(instance)
        if 'reverse' in self.context.keys():
            if self.context['reverse']:
                ordering = 'delta'
            else:
                ordering = '-delta'
            return positions.order_by(ordering).first().delta

    class Meta:
        model = Track
        fields = 'id', 'artist', 'title', 'has_cover', 'cover_url', 'has_distributor', 'distributor', \
                 'positions_count', 'max_position_delta'


class TrackForSearchExtendedSerializer(serializers.ModelSerializer):
    positions = serializers.SerializerMethodField()
    positions_count = serializers.SerializerMethodField()
    max_position_delta = serializers.SerializerMethodField()

    def _get_positions(self, instance):
        filter_params = {'track': instance}
        if 'service' in self.context.keys():
            filter_params['service'] = self.context['service']
        if 'deltas' in self.context.keys():
            filter_params['delta__isnull'] = False
        if 'dates' in self.context.keys():
            filter_params['date__in'] = self.context['dates']
        return Position.objects.filter(**filter_params).order_by('-date')

    def _get_max_delta_position(self, instance):
        positions = self._get_positions(instance)
        if 'reverse' in self.context.keys():
            if self.context['reverse']:
                ordering = 'delta'
            else:
                ordering = '-delta'
            return positions.order_by(ordering).first()

    def get_max_position_delta(self, instance):
        position = self._get_max_delta_position(instance)
        if position:
            return position.delta
        else:
            return None

    def get_positions_count(self, instance):
        positions = self._get_positions(instance)
        return positions.count()

    def get_positions(self, instance):
        if 'deltas' not in self.context.keys():
            positions = self._get_positions(instance)
            return PositionSimpleSerializer(positions, many=True).data
        else:
            position = self._get_max_delta_position(instance)
            return PositionSimpleSerializer(position).data

    class Meta:
        model = Track
        fields = 'id', 'artist', 'title', 'has_cover', 'cover_url', 'has_distributor', 'distributor', \
                 'positions_count', 'max_position_delta', 'positions'


class PositionSerializer(serializers.ModelSerializer):
    track = TrackSerializer()

    class Meta:
        model = Position
        fields = 'service', 'date', 'current', 'previous', 'delta', 'track'


class PositionSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = 'service', 'date', 'current', 'previous', 'delta'


class PositionForChartSerializer(serializers.ModelSerializer):
    track = serializers.SerializerMethodField()

    def get_track(self, instance):
        trck = Track.objects.filter(positions=instance).first()
        return TrackSerializer(trck, context=self.context).data

    class Meta:
        model = Position
        fields = 'current', 'previous', 'delta', 'track'


class ChartSerializer(serializers.ModelSerializer):
    positions = serializers.SerializerMethodField()

    def get_positions(self, instance):
        ordered_queryset = Position.objects.filter(chart=instance).order_by('current')
        return PositionForChartSerializer(ordered_queryset, many=True, context=self.context).data

    class Meta:
        model = Chart
        fields = 'date', 'service', 'positions'


class ChartGetSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    service = serializers.ChoiceField(choices=CHARTS)


class ChartGetAllSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)


class ChartAddSerializer(serializers.Serializer):
    service = serializers.ChoiceField(choices=CHARTS)
    date = serializers.DateField()


class ChartAddAllSerializer(serializers.Serializer):
    date = serializers.DateField()


class ChartAddPeriodSerializer(serializers.Serializer):
    service = serializers.ChoiceField(choices=CHARTS)
    date_from = serializers.DateField()
    date_to = serializers.DateField()


class ChartAddAllPeriodSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()


class ChartsSearchSerializer(serializers.Serializer):
    artist = serializers.CharField(required=False)
    title = serializers.CharField(required=False)
    extended = serializers.BooleanField(default=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, data):
        if 'artist' not in data.keys() and 'title' not in data.keys():
            raise serializers.ValidationError('artist or title required')
        return data


class ChartsGetTopSerializer(serializers.Serializer):
    service = serializers.ChoiceField(choices=CHARTS)
    top = serializers.IntegerField(required=False)
    extended = serializers.BooleanField(default=False)
    reverse = serializers.BooleanField(default=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class ChartsGetTrackSerializer(serializers.Serializer):
    service = serializers.ChoiceField(choices=CHARTS)
    id = serializers.IntegerField()


class ChartGetStatsSerializer(serializers.Serializer):
    service = serializers.ChoiceField(choices=CHARTS)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

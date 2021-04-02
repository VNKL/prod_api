from rest_framework import serializers

from .models import Analyzer


class AnalyzerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analyzer
        fields = 'id', 'owner', 'status', 'error', 'method', 'param', 'start_date', 'finish_date'


class AnalyzerExtendedSerializer(serializers.ModelSerializer):
    result = serializers.JSONField()

    class Meta:
        model = Analyzer
        fields = 'id', 'owner', 'status', 'error', 'method', 'param', 'start_date', 'finish_date', 'result'


class AnalyzerAddSerializer(serializers.Serializer):
    artist_url = serializers.CharField(max_length=100)


class AnalyzerGetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    extended = serializers.BooleanField(default=False)
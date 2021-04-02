from rest_framework import serializers

from .models import Account, Proxy


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'


class ProxySerializer(serializers.ModelSerializer):
    class Meta:
        model = Proxy
        fields = '__all__'


class AccountAddSerializer(serializers.Serializer):
    login = serializers.CharField(max_length=100)
    password = serializers.CharField(max_length=100)


class AccountResetSerializer(serializers.Serializer):
    login = serializers.CharField(required=False)
    user_id = serializers.IntegerField(required=False)
    is_alive = serializers.BooleanField(default=False)
    is_busy = serializers.BooleanField(default=False)
    is_rate_limited = serializers.BooleanField(default=False)
    rate_limit_date = serializers.BooleanField(default=False)


class ProxyAddSerializer(serializers.Serializer):
    proxy = serializers.CharField()
    period = serializers.IntegerField()

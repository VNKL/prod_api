from rest_framework import serializers
from rest_framework_jwt.settings import api_settings

from .models import User
from api.parsers.serializers import ParserSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = 'username', 'balance', 'ava_url', 'has_token', \
                 'can_ads', 'can_analyzers', 'can_charts', 'can_grabbers', 'can_parsers', 'can_related'


class UserExtendedSerializer(serializers.ModelSerializer):
    parsers = ParserSerializer(many=True)

    class Meta:
        model = User
        fields = 'username', 'balance', 'parsers'


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    @staticmethod
    def get_token(obj):
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(obj)
        token = jwt_encode_handler(payload)
        return token

    def create(self, validated_data):
        user = User.objects.create(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user

    class Meta:
        model = User
        fields = 'username', 'password'

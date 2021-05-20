from rest_framework import serializers

from .models import Parser, Item


class ParserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parser
        fields = 'id', 'status', 'error', 'n_last', 'type', 'start_date', 'finish_date'


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = 'name', 'share_users', 'share_items'


class ParserExtendedSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    def get_items(self, instance):
        ordered_queryset = Item.objects.filter(parser=instance).order_by('-share_users', '-share_items')
        return ItemSerializer(ordered_queryset, many=True, context=self.context).data

    class Meta:
        model = Parser
        fields = 'id', 'status', 'error', 'n_last', 'type', 'start_date', 'finish_date', 'items'


class CreateParserSerializer(serializers.Serializer):
    type = serializers.CharField(default='tracks')
    n_last = serializers.IntegerField(default=30)
    user_ids = serializers.CharField()


class GetParserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    extended = serializers.BooleanField(default=False)

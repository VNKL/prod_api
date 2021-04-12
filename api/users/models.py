from django.contrib.auth.models import User as DjangoUser
from django.db import models


class User(DjangoUser):
    DEFAULT_AVA_URL = 'http://my-engine.ru/modules/users/avatar.png'

    balance = models.IntegerField(default=0)
    ads_token = models.CharField(max_length=100, blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)
    ava_url = models.TextField(default=DEFAULT_AVA_URL)
    has_token = models.BooleanField(default=False)
    can_ads = models.BooleanField(default=False)
    can_analyzers = models.BooleanField(default=False)
    can_charts = models.BooleanField(default=False)
    can_grabbers = models.BooleanField(default=False)
    can_parsers = models.BooleanField(default=False)
    can_related = models.BooleanField(default=False)

    def __str__(self):
        return f'User "{self.username}"'

from django.db import models
from api.settings import DEFAULT_USER_AGENT


class Account(models.Model):
    login = models.CharField(max_length=100, blank=False, null=False)
    password = models.CharField(max_length=100, blank=False, null=False)
    token = models.CharField(max_length=100, blank=False, null=False)
    user_id = models.BigIntegerField(blank=False, null=False)
    is_alive = models.BooleanField(default=True)
    is_busy = models.BooleanField(default=False)
    is_rate_limited = models.BooleanField(default=False)
    rate_limit_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'VkAccount {self.user_id}'


class Proxy(models.Model):
    login = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    ip = models.CharField(max_length=50)
    port = models.CharField(max_length=10)
    is_alive = models.BooleanField(default=True)
    n_used = models.IntegerField(default=0)
    load_date = models.DateTimeField()
    expiration_date = models.DateTimeField()

    def __str__(self):
        return f'Proxy {self.login}:{self.password}@{self.ip}:{self.port}'


class ParsingThreadCount(models.Model):
    max_threads = models.IntegerField(default=64)
    offset_param = models.IntegerField(default=6400)
    savers_count_max_threads = models.IntegerField(default=8)
    savers_count_division_param = models.IntegerField(default=25)

    def __str__(self):
        return f'Current parsing max threads count: {self.max_threads}, offset param: {self.offset_param}'


class UserAgent(models.Model):
    user_agent = models.CharField(default=DEFAULT_USER_AGENT, max_length=200)

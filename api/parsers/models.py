from django.db import models

from api.users.models import User


class Parser(models.Model):
    STATUS_CHOICES = [[0, 'Ошибка'], [1, 'Выполняется'], [2, 'Завершено'], [3, 'Ожидает очереди']]

    owner = models.ForeignKey(User, related_name='parsers', on_delete=models.CASCADE)
    status = models.IntegerField(default=3, blank=False, null=False, choices=STATUS_CHOICES)
    error = models.TextField(blank=True, null=True)
    method = models.CharField(max_length=100, blank=False, null=False)
    param = models.TextField(blank=True, null=True)
    count_only = models.BooleanField(default=True)
    start_date = models.DateTimeField(blank=False, null=False)
    finish_date = models.DateTimeField(blank=True, null=True)
    savers_count = models.BigIntegerField(blank=True, null=True)
    audios_count = models.BigIntegerField(blank=True, null=True)
    result_path = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Parser {self.pk} for method "{self.method}" by user "{self.owner.username}"'


class Audio(models.Model):
    parser = models.ForeignKey(Parser, related_name='audios', on_delete=models.CASCADE)
    parsing_date = models.DateTimeField(blank=False, null=False)
    owner_id = models.BigIntegerField(blank=False, null=False)
    audio_id = models.BigIntegerField(blank=False, null=False)
    artist = models.TextField(blank=False, null=False)
    title = models.TextField(blank=False, null=False)
    date = models.DateTimeField(blank=True, null=True)
    chart_position = models.IntegerField(blank=True, null=True)
    post_owner_id = models.BigIntegerField(blank=True, null=True)
    post_id = models.BigIntegerField(blank=True, null=True)
    savers_count = models.BigIntegerField(default=0)
    source = models.TextField(blank=True, null=True)
    doubles = models.IntegerField(default=0, blank=True, null=True)

    def __str__(self):
        return f'Audio "{self.artist} - {self.title}"'

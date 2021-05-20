from django.db import models

from api.users.models import User


class Parser(models.Model):
    STATUS_CHOICES = [[0, 'Ошибка'], [1, 'Выполняется'], [2, 'Завершено'], [3, 'Ожидает очереди'], [4, 'Отменено']]
    TYPE_CHOICES = [['tracks', 'Треки'], ['artists', 'Артисты']]

    owner = models.ForeignKey(User, related_name='users_audios_parsers', on_delete=models.CASCADE)
    status = models.IntegerField(blank=False, null=False, choices=STATUS_CHOICES)
    error = models.TextField(blank=True, null=True)
    n_last = models.BigIntegerField(default=30)
    type = models.TextField(choices=TYPE_CHOICES)
    user_ids = models.TextField(null=True)
    start_date = models.DateTimeField()
    finish_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'Users audios parser {self.pk} by user "{self.owner.username}"'


class Item(models.Model):
    parser = models.ForeignKey(Parser, related_name='items', on_delete=models.CASCADE)
    name = models.TextField()
    share_users = models.FloatField(null=True)
    share_items = models.FloatField(null=True)

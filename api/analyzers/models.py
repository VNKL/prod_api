from django.db import models

from api.users.models import User


class Analyzer(models.Model):
    STATUS_CHOICES = [[0, 'Ошибка'], [1, 'Выполняется'], [2, 'Завершено'], [3, 'Ожидает очереди'], [4, 'Отменено']]

    owner = models.ForeignKey(User, related_name='analyzers', on_delete=models.CASCADE)
    status = models.IntegerField(blank=False, null=False, choices=STATUS_CHOICES)
    error = models.TextField(blank=True, null=True)
    method = models.CharField(max_length=100, blank=False, null=False)
    param = models.TextField(blank=True, null=True)
    artist_name = models.TextField(blank=True, null=True)
    photo_url = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField(blank=False, null=False)
    finish_date = models.DateTimeField(blank=True, null=True)
    result = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Analyzer {self.pk} for method "{self.method}" by user "{self.owner.username}"'

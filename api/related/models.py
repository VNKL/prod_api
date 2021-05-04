from django.db import models

from api.users.models import User


class Scanner(models.Model):
    STATUS_CHOICES = [[0, 'Ошибка'], [1, 'Выполняется'], [2, 'Завершено'], [3, 'Ожидает очереди'], [4, 'Отменено']]

    owner = models.ForeignKey(User, related_name='related_scanners', on_delete=models.CASCADE)
    status = models.IntegerField(blank=False, null=False, choices=STATUS_CHOICES)
    error = models.TextField(blank=True, null=True)
    artist_url = models.TextField()
    artist_name = models.TextField(blank=True, null=True)
    photo_url = models.TextField(blank=True, null=True)
    related_count = models.BigIntegerField(blank=True, null=True)
    listens_min = models.BigIntegerField(default=25000)
    listens_max = models.BigIntegerField(default=75000)
    n_releases = models.IntegerField(default=5)
    last_days = models.IntegerField(default=60)
    median_days = models.IntegerField(default=60)
    recurse = models.IntegerField(default=1)
    start_date = models.DateTimeField()
    finish_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'Scanner {self.pk} by user "{self.owner.username}"'


class Artist(models.Model):
    scanners = models.ManyToManyField(Scanner, related_name='related')
    name = models.TextField()
    card_url = models.TextField()
    group_name = models.TextField(blank=True, null=True)
    group_url = models.TextField(blank=True, null=True)
    user_name = models.TextField(blank=True, null=True)
    user_url = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Artist "{self.name}"'

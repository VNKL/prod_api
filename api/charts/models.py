from django.db import models

from api.settings import CHARTS_FULL_NAMES


SERVICES = [[key, val] for key, val in CHARTS_FULL_NAMES.items()]


class Chart(models.Model):
    date = models.DateTimeField()
    service = models.CharField(max_length=20, choices=SERVICES)

    def __str__(self):
        return f'Chart for date {self.date}'


class Position(models.Model):
    chart = models.ForeignKey(Chart, related_name='positions', on_delete=models.CASCADE)
    service = models.CharField(max_length=20, choices=SERVICES)
    date = models.DateTimeField()
    current = models.IntegerField()
    previous = models.IntegerField(blank=True, null=True)
    delta = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f'Chart {self.service} Position #{self.current} for date {self.date}'


class Track(models.Model):
    positions = models.ManyToManyField(Position, related_name='track')
    artist = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    has_cover = models.BooleanField(default=False)
    cover_url = models.TextField(blank=True, null=True)
    has_distributor = models.BooleanField(default=False)
    distributor = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f'Chart Track "{self.artist} - {self.title}"'

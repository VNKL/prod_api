from django.db import models

from api.users.models import User


class Grabber(models.Model):
    STATUS_CHOICES = [
        [0, 'Ошибка'],
        [1, 'Выполняется'],
        [2, 'Завершено']
    ]
    owner = models.ForeignKey(User, related_name='grabbers', on_delete=models.CASCADE)
    status = models.IntegerField(blank=False, null=False, choices=STATUS_CHOICES)
    error = models.TextField(blank=True, null=True)
    group = models.CharField(max_length=100)
    with_audio = models.BooleanField(default=True)
    ads_only = models.BooleanField(default=False)
    with_ads = models.BooleanField(default=False)
    date_from = models.DateField(blank=True, null=True)
    date_to = models.DateField(blank=True, null=True)
    start_date = models.DateTimeField(blank=False, null=False)
    finish_date = models.DateTimeField(blank=True, null=True)
    posts_count = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f'Grabber {self.pk} for group "{self.group}" by user "{self.owner.username}"'


class Post(models.Model):
    grabbers = models.ManyToManyField(Grabber, related_name='posts')
    owner_id = models.IntegerField()
    post_id = models.IntegerField()
    date = models.DateTimeField()
    is_ad = models.BooleanField()
    likes = models.IntegerField()
    reposts = models.IntegerField()
    comments = models.IntegerField()
    has_playlist = models.BooleanField()
    has_audios = models.BooleanField()
    text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Post {self.owner_id}_{self.post_id}'


class Playlist(models.Model):
    posts = models.ManyToManyField(Post, related_name='playlists')
    owner_id = models.IntegerField()
    playlist_id = models.IntegerField()
    access_hash = models.CharField(max_length=100, blank=True, null=True)
    listens = models.IntegerField(blank=True, null=True)
    followers = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=100)
    create_date = models.DateTimeField(blank=True, null=True)
    update_date = models.DateTimeField(blank=True, null=True)
    parsing_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'Playlist "{self.title}"'


class Audio(models.Model):
    posts = models.ManyToManyField(Post, related_name='audios')
    owner_id = models.IntegerField(blank=False, null=False)
    audio_id = models.IntegerField(blank=False, null=False)
    artist = models.CharField(max_length=100, blank=False, null=False)
    title = models.CharField(max_length=100, blank=False, null=False)
    date = models.DateTimeField(blank=True, null=True)
    savers_count = models.IntegerField(blank=True, null=True)
    doubles = models.IntegerField(blank=True, null=True)
    source = models.CharField(max_length=10, blank=True, null=True)
    parsing_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'Audio "{self.artist} - {self.title}"'
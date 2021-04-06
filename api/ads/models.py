from django.db import models

from api.users.models import User


class Campaign(models.Model):
    STATUS_CHOICES = [[0, 'Остановлена'], [1, 'Запущена'], [2, 'Удалена'], [3, 'Ошибка'],
                      [4, 'Ождает очереди'], [5, 'Запускается']]
    AGE_DISCLAIMER_CHOICES = [[0, 'Отсутствует'], [1, '0+'], [2, '6+'], [3, '12+'], [4, '16+'], [5, '18+']]
    DEFAULT_COVER_URL = 'https://cdn.dribbble.com/users/29051/screenshots/2515769/icon.png'

    owner = models.ForeignKey(User, related_name='campaigns', on_delete=models.CASCADE)
    cabinet_id = models.IntegerField()
    cabinet_name = models.TextField()
    client_id = models.IntegerField(blank=True, null=True)
    client_name = models.TextField(blank=True, null=True)
    campaign_id = models.IntegerField(blank=True, null=True)
    campaign_name = models.TextField()
    money_limit = models.IntegerField()
    reference = models.TextField(blank=True, null=True)
    reference_url = models.CharField(max_length=100)
    sex = models.CharField(max_length=10, blank=True, null=True)
    music = models.BooleanField(default=False)
    boom = models.BooleanField(default=False)
    empty_ads = models.IntegerField(default=0)
    age_disclaimer = models.IntegerField(default=5, choices=AGE_DISCLAIMER_CHOICES)
    age_from = models.IntegerField(default=0)
    age_to = models.IntegerField(default=0)
    musicians = models.TextField(blank=True, null=True)
    groups = models.TextField(blank=True, null=True)
    related = models.BooleanField(default=False)
    retarget = models.TextField(blank=True, default=True)
    artist = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    cover_url = models.TextField(default=DEFAULT_COVER_URL)
    group_id = models.IntegerField()
    fake_group_id = models.IntegerField(blank=True, null=True)
    spent = models.FloatField(default=0.0)
    reach = models.IntegerField(default=0)
    cpm = models.FloatField(default=0.0)
    listens = models.IntegerField(default=0)
    cpl = models.FloatField(default=0)
    lr = models.FloatField(default=0)
    saves = models.IntegerField(default=0)
    cps = models.FloatField(default=0)
    sr = models.FloatField(default=0)
    clicks = models.IntegerField(default=0)
    cpc = models.FloatField(default=0)
    cr = models.FloatField(default=0)
    joins = models.IntegerField(default=0)
    cpj = models.FloatField(default=0)
    jr = models.FloatField(default=0)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(blank=True, null=True)
    status = models.IntegerField(default=4, choices=STATUS_CHOICES)
    errors = models.TextField(blank=True, null=True)
    is_automate = models.BooleanField(default=False)
    has_moderate_audios = models.BooleanField(default=False)
    audios_is_moderated = models.BooleanField(default=False)
    audience_count = models.IntegerField(default=0)

    def __str__(self):
        return f'Campaign "{self.artist} - {self.title}"'


class Ad(models.Model):
    STATUS_CHOICES = [[0, 'Остановлено'], [1, 'Запущено'], [2, 'Удалено']]
    APPROVED_CHOICES = [[0, 'Не модерировалось'], [1, 'На модерации'], [2, 'Одобрено'], [3, 'Отклонено']]

    campaign = models.ForeignKey(Campaign, related_name='ads', on_delete=models.CASCADE)
    ad_id = models.IntegerField()
    ad_name = models.TextField()
    post_owner = models.IntegerField()
    post_id = models.IntegerField()
    status = models.IntegerField(default=1, choices=STATUS_CHOICES)
    approved = models.IntegerField(default=1, choices=APPROVED_CHOICES)
    spent = models.FloatField(default=0.0)
    reach = models.IntegerField(default=0)
    cpm = models.FloatField(default=30.0)
    listens = models.IntegerField(default=0)
    cpl = models.FloatField(default=0)
    lr = models.FloatField(default=0)
    saves = models.IntegerField(default=0)
    cps = models.FloatField(default=0)
    sr = models.FloatField(default=0)
    clicks = models.IntegerField(default=0)
    cpc = models.FloatField(default=0)
    cr = models.FloatField(default=0)
    joins = models.IntegerField(default=0)
    cpj = models.FloatField(default=0)
    jr = models.FloatField(default=0)
    audience_count = models.IntegerField(default=0)
    cpm_price = models.IntegerField(default=30)

    def __str__(self):
        return f'Ad "{self.ad_name}" in {self.campaign}'


class Playlist(models.Model):
    ad = models.ForeignKey(Ad, related_name='playlists', on_delete=models.CASCADE)
    owner_id = models.IntegerField()
    playlist_id = models.IntegerField()
    access_key = models.CharField(max_length=100, blank=True, null=True)
    title = models.TextField()
    listens = models.IntegerField(default=0)
    followers = models.IntegerField(default=0)

    def __str__(self):
        return f'Playlist "{self.title}"'


class Audio(models.Model):
    ad = models.ForeignKey(Ad, related_name='audios', on_delete=models.CASCADE)
    owner_id = models.IntegerField(blank=True, null=True)
    audio_id = models.IntegerField(blank=True, null=True)
    in_playlist = models.BooleanField(null=True)
    artist = models.TextField()
    title = models.TextField()
    savers_count = models.IntegerField(default=0)

    def __str__(self):
        return f'Audio "{self.artist} - {self.title}"'


class Automate(models.Model):
    TYPE_CHOICES = [[0, 'По прослушиваниям'], [1, 'По добавлениям']]
    STATUS_CHOICES = [[0, 'Остановлена'], [1, 'Запущена'], [2, 'Ожидает запуска'], [3, 'Ошибка']]
    START_CHOICES = [[0, 'Сейчас'], [1, 'Завтра']]
    FINISH_CHOICES = [[0, '23:59'], [1, 'Вручную']]

    campaign = models.ForeignKey(Campaign, related_name='automates', on_delete=models.CASCADE)
    type = models.IntegerField(default=1, choices=TYPE_CHOICES)
    target_cost = models.FloatField()
    status = models.IntegerField(default=1, choices=STATUS_CHOICES)
    start = models.IntegerField(default=0, choices=START_CHOICES)
    finish = models.IntegerField(default=0, choices=FINISH_CHOICES)
    create_date = models.DateTimeField()
    finish_date = models.DateTimeField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Automate for {self.campaign}'

# Generated by Django 3.1.6 on 2021-04-03 21:20

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Audio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner_id', models.IntegerField()),
                ('audio_id', models.IntegerField()),
                ('artist', models.CharField(max_length=100)),
                ('title', models.CharField(max_length=100)),
                ('date', models.DateTimeField(blank=True, null=True)),
                ('savers_count', models.IntegerField(blank=True, null=True)),
                ('doubles', models.IntegerField(blank=True, null=True)),
                ('source', models.CharField(blank=True, max_length=10, null=True)),
                ('parsing_date', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Grabber',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.IntegerField(choices=[[0, 'Ошибка'], [1, 'Выполняется'], [2, 'Завершено']])),
                ('error', models.TextField(blank=True, null=True)),
                ('group', models.CharField(max_length=100)),
                ('with_audio', models.BooleanField(default=True)),
                ('ads_only', models.BooleanField(default=False)),
                ('with_ads', models.BooleanField(default=False)),
                ('date_from', models.DateField(blank=True, null=True)),
                ('date_to', models.DateField(blank=True, null=True)),
                ('start_date', models.DateTimeField()),
                ('finish_date', models.DateTimeField(blank=True, null=True)),
                ('posts_count', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner_id', models.IntegerField()),
                ('post_id', models.IntegerField()),
                ('date', models.DateTimeField()),
                ('is_ad', models.BooleanField()),
                ('likes', models.IntegerField()),
                ('reposts', models.IntegerField()),
                ('comments', models.IntegerField()),
                ('has_playlist', models.BooleanField()),
                ('has_audios', models.BooleanField()),
                ('text', models.TextField(blank=True, null=True)),
                ('grabbers', models.ManyToManyField(related_name='posts', to='grabbers.Grabber')),
            ],
        ),
        migrations.CreateModel(
            name='Playlist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner_id', models.IntegerField()),
                ('playlist_id', models.IntegerField()),
                ('access_hash', models.CharField(blank=True, max_length=100, null=True)),
                ('listens', models.IntegerField(blank=True, null=True)),
                ('followers', models.IntegerField(blank=True, null=True)),
                ('title', models.CharField(max_length=100)),
                ('create_date', models.DateTimeField(blank=True, null=True)),
                ('update_date', models.DateTimeField(blank=True, null=True)),
                ('parsing_date', models.DateTimeField(blank=True, null=True)),
                ('posts', models.ManyToManyField(related_name='playlists', to='grabbers.Post')),
            ],
        ),
    ]

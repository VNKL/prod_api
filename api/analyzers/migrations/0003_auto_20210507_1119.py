# Generated by Django 3.1.6 on 2021-05-07 08:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analyzers', '0002_analyzer_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='analyzer',
            name='artist_name',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='analyzer',
            name='photo_url',
            field=models.TextField(blank=True, null=True),
        ),
    ]

# Generated by Django 3.1.6 on 2021-09-20 11:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_useragent'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UserAgent',
        ),
    ]

# Generated by Django 3.1.6 on 2021-05-03 12:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_remove_user_is_testing'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='user_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
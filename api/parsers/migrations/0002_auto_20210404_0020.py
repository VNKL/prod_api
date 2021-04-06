# Generated by Django 3.1.6 on 2021-04-03 21:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
        ('parsers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='parser',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parsers', to='users.user'),
        ),
        migrations.AddField(
            model_name='audio',
            name='parser',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audios', to='parsers.parser'),
        ),
    ]
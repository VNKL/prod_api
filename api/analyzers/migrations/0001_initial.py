# Generated by Django 3.1.6 on 2021-04-03 21:20

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Analyzer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.IntegerField(choices=[[0, 'Ошибка'], [1, 'Выполняется'], [2, 'Завершено']])),
                ('error', models.TextField(blank=True, null=True)),
                ('method', models.CharField(max_length=100)),
                ('param', models.TextField(blank=True, null=True)),
                ('start_date', models.DateTimeField()),
                ('finish_date', models.DateTimeField(blank=True, null=True)),
                ('result', models.TextField(blank=True, null=True)),
            ],
        ),
    ]

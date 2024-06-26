# Generated by Django 3.1.6 on 2021-04-06 15:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parsers', '0002_auto_20210404_0020'),
    ]

    operations = [
        migrations.AlterField(
            model_name='audio',
            name='artist',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='audio',
            name='source',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='audio',
            name='title',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='parser',
            name='result_path',
            field=models.TextField(blank=True, null=True),
        ),
    ]

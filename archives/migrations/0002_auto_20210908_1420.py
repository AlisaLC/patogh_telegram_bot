# Generated by Django 3.2.7 on 2021-09-08 14:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archives', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='classnote',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='classvideo',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),
    ]

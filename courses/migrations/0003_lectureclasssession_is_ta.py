# Generated by Django 3.2.7 on 2021-09-22 20:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_lectureclasssession'),
    ]

    operations = [
        migrations.AddField(
            model_name='lectureclasssession',
            name='is_ta',
            field=models.BooleanField(default=False),
        ),
    ]
# Generated by Django 3.2.7 on 2021-09-25 00:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0003_lectureclasssession_is_ta'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lecturesession',
            name='day',
            field=models.CharField(choices=[('0', 'Saturday'), ('1', 'Sunday'), ('2', 'Monday'), ('3', 'Tuesday'), ('4', 'Wednesday'), ('5', 'Thursday'), ('6', 'Friday')], max_length=1),
        ),
    ]

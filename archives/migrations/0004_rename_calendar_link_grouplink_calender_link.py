# Generated by Django 3.2.7 on 2021-09-24 07:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('archives', '0003_auto_20210924_0736'),
    ]

    operations = [
        migrations.RenameField(
            model_name='grouplink',
            old_name='calendar_link',
            new_name='calender_link',
        ),
    ]

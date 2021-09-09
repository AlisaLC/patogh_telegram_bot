# Generated by Django 3.2.6 on 2021-08-24 19:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=1000)),
            ],
        ),
        migrations.CreateModel(
            name='Lecture',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group_id', models.TextField()),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.course')),
            ],
        ),
        migrations.CreateModel(
            name='Lecturer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=1000)),
            ],
        ),
        migrations.CreateModel(
            name='LectureSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('day', models.CharField(choices=[(0, 'Saturday'), (1, 'Sunday'), (2, 'Monday'), (3, 'Tuesday'), (4, 'Wednesday'), (5, 'Thursday'), (6, 'Friday')], max_length=1)),
                ('lecture', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.lecture')),
            ],
        ),
        migrations.CreateModel(
            name='LectureClassSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_number', models.IntegerField()),
                ('date', models.DateField()),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.course')),
            ],
        ),
        migrations.AddField(
            model_name='course',
            name='field',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.field'),
        ),
        migrations.AddField(
            model_name='course',
            name='lecturer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.lecturer'),
        ),
    ]

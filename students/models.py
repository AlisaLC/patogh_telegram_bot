from django.db import models

from courses.models import Lecture


class Student(models.Model):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    student_id = models.IntegerField(default=-1)
    lectures = models.ManyToManyField(Lecture)

    def __str__(self):
        return str(self.student_id) + ' - ' + self.first_name + ' ' + self.last_name

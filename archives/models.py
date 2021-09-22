from django.db import models

from courses.models import LectureClassSession, Course
from students.models import Student


class ClassVideo(models.Model):
    link = models.CharField(max_length=2000)
    subject = models.CharField(max_length=1000, default=' - ')
    lecture_class_session = models.ForeignKey(LectureClassSession, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return str(self.lecture_class_session) + ' - ' + str(self.subject)


class ClassNote(models.Model):
    link = models.CharField(max_length=2000)
    subject = models.CharField(max_length=1000, default=' - ')
    lecture_class_session = models.ForeignKey(LectureClassSession, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return str(self.lecture_class_session) + ' - ' + str(self.subject)


class GroupLink(models.Model):
    class_link = models.TextField(default=' - ')
    source_link = models.TextField(default=' - ')
    telegram_link = models.TextField(default=' - ')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.course)

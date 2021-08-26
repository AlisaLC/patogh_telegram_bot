from django.db import models

from courses.models import Course
from students.models import Student


class Feedback(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    feedback = models.TextField()
    is_verified = models.BooleanField(default=False)


class FeedbackLike(models.Model):
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

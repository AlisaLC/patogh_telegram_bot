from django.db import models


class Field(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=1000)

    def __str__(self):
        return str(self.id) + ' - ' + self.name


class Lecturer(models.Model):
    name = models.CharField(max_length=1000)

    def __str__(self):
        return self.name


class Course(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    lecturer = models.ForeignKey(Lecturer, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.field) + ' - ' + str(self.lecturer)


class Lecture(models.Model):
    group_id = models.IntegerField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.course.field.id) + '-' + str(self.group_id) + ' - ' + self.course.field.name + ' - ' + \
               str(self.course.lecturer)


class LectureSession(models.Model):
    DAYS_OF_WEEK = (
        (0, 'Saturday'),
        (1, 'Sunday'),
        (2, 'Monday'),
        (3, 'Tuesday'),
        (4, 'Wednesday'),
        (5, 'Thursday'),
        (6, 'Friday'),
    )

    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()
    day = models.CharField(max_length=1, choices=DAYS_OF_WEEK)

    def __str__(self):
        return str(self.lecture) + ' - ' + self.day + ' from ' + str(self.start_time) + ' to ' + str(self.end_time)


class LectureClassSession(models.Model):
    session_number = models.IntegerField()
    date = models.DateField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    is_ta = models.BooleanField(default=False)

    def __str__(self):
        return ('TA ' if self.is_ta else '') + str(self.course) + ' - ' + str(self.date)

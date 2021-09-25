from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=1000)
    shortname = models.CharField(max_length=5)

    def __str__(self):
        return self.name + ' - ' + self.shortname


# def get_default_department():
#     return Department.objects.get_or_create(name='دانشکده مهندسی کامپیوتر', shortname='CE')


class Field(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=1000)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return str(self.id) + ' - ' + self.name + ' - ' + str(self.department)


class Lecturer(models.Model):
    name = models.CharField(max_length=1000)
    mail = models.EmailField(default=' - ')

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

    def __str__(self):
        return str(self.id) + ' - ' + str(self.course) + ' - ' + str(self.date)

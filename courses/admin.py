from django.contrib import admin

from .models import Field, Lecturer, Course, Lecture, LectureSession, LectureClassSession, Department

admin.site.register(Department)
admin.site.register(Field)
admin.site.register(Lecturer)
admin.site.register(Course)
admin.site.register(Lecture)
admin.site.register(LectureSession)
admin.site.register(LectureClassSession)

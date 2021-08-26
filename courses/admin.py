from django.contrib import admin

from .models import Field, Lecturer, Course, Lecture, LectureSession

admin.site.register(Field)
admin.site.register(Lecturer)
admin.site.register(Course)
admin.site.register(Lecture)
admin.site.register(LectureSession)

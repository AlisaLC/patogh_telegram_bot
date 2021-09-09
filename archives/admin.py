from django.contrib import admin

# Register your models here.
from archives.models import ClassVideo, ClassNote

admin.site.register(ClassVideo)
admin.site.register(ClassNote)
# admin.site.register(GroupLink)

from django.contrib import admin

# Register your models here.
from archives.models import ClassVideo, ClassNote, GroupLink

admin.site.register(ClassVideo)
admin.site.register(ClassNote)
admin.site.register(GroupLink)

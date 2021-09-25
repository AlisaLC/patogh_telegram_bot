import datetime

from django.conf import settings
from django.core.management import BaseCommand
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from courses.models import LectureSession, LectureClassSession


class Command(BaseCommand):
    def handle(self, *args, **options):
        app = Client('patogh_bot', bot_token=settings.BOT_TOKEN, api_id=settings.BOT_API_ID,
                     api_hash=settings.BOT_API_HASH)
        current_time = datetime.datetime.now()
        current_day = datetime.datetime.today()
        lecture_sessions = LectureSession.objects.filter(
            start_time__lt=(current_time + datetime.timedelta(minutes=15)).strftime('%H:%M'),
            end_time__gt=current_time.strftime('%H:%M'),
            day=(current_day.weekday() + 2) % 7).all()
        with app:
            for lecture_session in lecture_sessions:
                current_lecture_class_session = LectureClassSession.objects.filter(
                    course_id=lecture_session.lecture.course.id, date=current_day).first()
                if current_lecture_class_session:
                    continue
                session_number = 1
                try:
                    session_number = LectureClassSession.objects.filter(
                        course_id=lecture_session.lecture.course.id).latest(
                        'session_number').session_number + 1
                except:
                    session_number = 1
                LectureClassSession.objects.create(course=lecture_session.lecture.course, date=current_day,
                                                   session_number=session_number)
                class_url = lecture_session.lecture.course.grouplink_set.first()
                if class_url and class_url.class_link.strip() != '-':
                    class_url = class_url.class_link
                else:
                    class_url = 'https://cw.sharif.edu/'
                for student in lecture_session.lecture.student_set.all():
                    bot_user = student.botuser_set.first()
                    app.send_message(
                        bot_user.chat_id,
                        student.first_name + ' عزیز\nکلاس درس ' + lecture_session.lecture.course.field.name
                        + ' استاد ' + lecture_session.lecture.course.lecturer.name +
                        ' رو یادت نره توش شرکت کنی!',
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                'ورود به کلاس',
                                url=class_url
                            )]]))

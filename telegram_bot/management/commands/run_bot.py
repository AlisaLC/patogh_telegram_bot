import re
import time

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, OperationalError
from django.db.models import Count
from pykeyboard import InlineKeyboard
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

from archives.models import ClassVideo, ClassNote, GroupLink
from courses.models import Field, Course, Lecture
from courses.models import LectureClassSession
from feedbacks.models import Feedback, FeedbackLike
from students.models import Student
from telegram_bot.models import BotUser, BotUserState


class Command(BaseCommand):

    def handle(self, *args, **options):
        BotHandler(self)


def connection_check():
    def decorate(func):
        def call(*args, **kwargs):
            django.db.close_old_connections()
            result = func(*args, **kwargs)
            return result

        return call

    return decorate


class BotHandler:
    app = Client('patogh_bot', bot_token=settings.BOT_TOKEN, api_id=settings.BOT_API_ID, api_hash=settings.BOT_API_HASH)
    session = requests.Session()

    def __init__(self, command):
        self.command = command
        if not BotHandler.session.cookies.get_dict().get('sessionid'):
            BotHandler.login_session(BotHandler.session, '99123456')
        self.app.run()

    AUTHORIZATION_FIRST_NAME_FILTER = filters.create(
        lambda _, __, message: BotUser.objects.filter(
            user_id=message.from_user.id).get().state.state == BotUserState.STATES[2][0] and BotUser.objects.filter(
            user_id=message.from_user.id).get().state.data == 'FIRST_NAME')
    AUTHORIZATION_LAST_NAME_FILTER = filters.create(
        lambda _, __, message: BotUser.objects.filter(
            user_id=message.from_user.id).get().state.state == BotUserState.STATES[2][0] and BotUser.objects.filter(
            user_id=message.from_user.id).get().state.data == 'LAST_NAME')
    AUTHORIZATION_STUDENT_ID_FILTER = filters.create(
        lambda _, __, message: BotUser.objects.filter(
            user_id=message.from_user.id).get().state.state == BotUserState.STATES[2][0] and BotUser.objects.filter(
            user_id=message.from_user.id).get().state.data == 'STUDENT_ID')
    FEEDBACK_SUBMIT_FILTER = filters.create(
        lambda _, __, message: BotUser.objects.filter(
            user_id=message.from_user.id).get().state.state == BotUserState.STATES[1][0])
    ARCHIVE_ADD_FILE_LINK_FILTER = filters.create(
        lambda _, __, message: BotUser.objects.filter(
            user_id=message.from_user.id).get().state.state == BotUserState.STATES[3][0])

    # ARCHIVE_ADD_SUBJECT_FILTER = filters.create(
    #     lambda _, __, message: BotUser.objects.filter(
    #         user_id=message.from_user.id).get().state.state == BotUserState.STATES[3][0] and BotUser.objects.filter(
    #         user_id=message.from_user.id).get().state.data == 'SUBJECT')

    @staticmethod
    def arrange_per_row_max(matrix: list[list[InlineKeyboardButton]], n: int) -> list[list[InlineKeyboardButton]]:
        output = []
        for rows in matrix:
            for item in rows:
                if output and len(output[-1]) < n:
                    output[-1].append(item)
                    continue
                output.append([item])
        return output

    @staticmethod
    def user_state_reset(user):
        user.state.state = BotUserState.STATES[0][0]
        user.state.data = ''
        user.state.save()

    @staticmethod
    @connection_check()
    @app.on_message(filters.command('start') & filters.private)
    def user_start(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).first()
        if user:
            user.chat_id = message.chat.id
            user.save()
        else:
            user = BotUser(user_id=message.from_user.id, chat_id=message.chat.id)
            user.state = BotUserState.objects.create(state=BotUserState.STATES[0][0], data='')
            user.student = Student.objects.create()
            user.save()
            message.reply_text('دانشجوی گرامی لطفاً هر چه زودتر هویت خود را از طریق دستور /authorize احراز نمایید.')

    @staticmethod
    @connection_check()
    @app.on_message(filters.command('cancel') & filters.private)
    def user_cancel(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        BotHandler.user_state_reset(user)
        message.reply_text('درخواست شما لغو شد.')

    @staticmethod
    @connection_check()
    @app.on_message(filters.command('authorize') & filters.private)
    def user_authorize(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        message.reply_text('نام کوچک خود را وارد کنید.')
        user.state.state = BotUserState.STATES[2][0]
        user.state.data = 'FIRST_NAME'
        user.state.save()

    @staticmethod
    @connection_check()
    @app.on_message(
        filters.text & filters.private & AUTHORIZATION_FIRST_NAME_FILTER)
    def authorization_first_name(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        user.student.first_name = message.text
        user.student.save()
        user.state.data = 'LAST_NAME'
        user.state.save()
        message.reply_text('نام خانوادگی خود را وارد کنید.')

    @staticmethod
    @connection_check()
    @app.on_message(
        filters.text & filters.private & AUTHORIZATION_LAST_NAME_FILTER)
    def authorization_last_name(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        user.student.last_name = message.text
        user.student.save()
        user.state.data = 'STUDENT_ID'
        user.state.save()
        message.reply_text('شماره دانشجویی خود را وارد کنید.')

    @staticmethod
    @connection_check()
    @app.on_message(
        filters.text & filters.private & AUTHORIZATION_STUDENT_ID_FILTER)
    def authorization_student_id(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        user.student.student_id = message.text
        user.student.save()
        BotHandler.user_state_reset(user)
        message.reply_text('با موفقیت احراز هویت شدید. هویت شما کاملاً محفوظ است و تنها برای اطلاع‌رسانی به شما '
                           'مورداستفاده قرار خواهد گرفت.')

    @staticmethod
    @connection_check()
    @app.on_message(filters.command('subscribe') & filters.private)
    def subscribe_start(_, message: Message):
        fields = Field.objects.all()
        message.reply_text(
            "به این بخش جدید خوش آمدید",
            reply_markup=InlineKeyboardMarkup(BotHandler.arrange_per_row_max([
                [
                    InlineKeyboardButton(
                        field.name,
                        callback_data='subscribe-field-' + str(field.id)
                    )
                    for field in fields
                ]
            ], 3)),
            reply_to_message_id=message.message_id
        )

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'subscribe_start'))
    def subscribe_start_by_back(_, callback: CallbackQuery):
        print("Back")
        fields = Field.objects.all()
        callback.message.edit_text(
            "به این بخش جدید خوش آمدید",
            reply_markup=InlineKeyboardMarkup(BotHandler.arrange_per_row_max([
                [
                    InlineKeyboardButton(
                        field.name,
                        callback_data='subscribe-field-' + str(field.id)
                    )
                    for field in fields
                ]
            ], 3))
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'subscribe-field-(\d+)'))
    def subscribe_course(_, callback: CallbackQuery):
        field_id = callback.matches[0].group(1)
        courses = Course.objects.filter(field_id=field_id).all()
        keyboard = BotHandler.arrange_per_row_max([
            [
                InlineKeyboardButton(
                    course.lecturer.name,
                    callback_data='subscribe-course-' + str(course.id) + '-b' + field_id
                )
                for course in courses
            ]
        ], 3)
        keyboard.append([InlineKeyboardButton(
            'بازگشت⬅️',
            callback_data='subscribe_start'
        )])
        callback.message.edit_text(
            "کدوم استاد؟🤔",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'subscribe-course-(\d+)-b(\d+)'))
    def subscribe_lecture_selection(_, callback: CallbackQuery):
        course_id = callback.matches[0].group(1)
        course = Course.objects.filter(id=course_id).get()
        field_id = callback.matches[0].group(2)
        lectures = Lecture.objects.filter(course=course).all()
        keyboard = BotHandler.arrange_per_row_max([
            [
                InlineKeyboardButton(
                    lecture.course.field.name + ' - گروه ' + str(lecture.group_id),
                    callback_data='subscribe-selection-lecture-' + str(lecture.id)
                )
                for lecture in lectures
            ]
        ], 1)
        keyboard.append([InlineKeyboardButton(
            'بازگشت⬅️',
            callback_data='subscribe-field-' + str(field_id)
        )])
        callback.message.edit_text(
            "گروه مورد نظر را انتخاب کنید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'subscribe-selection-lecture-(\d+)'))
    def subscribe_selection_lecture(_, callback: CallbackQuery):
        lecture_id = callback.matches[0].group(1)
        lecture = Lecture.objects.filter(id=lecture_id).get()
        course = lecture.course
        keyboard = InlineKeyboard()
        subscribe_string = 'subscribe-add-lecture-' + str(lecture_id) + '-to-student-lectures'
        unsubscribe_string = 'unsubscribe-add-lecture-' + str(lecture_id) + '-to-student-lectures'
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        student = user.student
        print(student.lectures.filter(id=lecture_id).exists())
        is_subscribed = student.lectures.filter(id=lecture_id).exists()
        keyboard.row(
            InlineKeyboardButton(
                "دیگر مایل به دنبال کردن این درس نیستم" if is_subscribed else "دنبال کردن این گروه",
                callback_data=subscribe_string if is_subscribed else unsubscribe_string
            )
        )
        keyboard.row(
            InlineKeyboardButton(
                'بازگشت⬅️',
                callback_data='subscribe-course-' + str(course.id) + '-b' + str(course.field.id)
            )
        )
        callback.message.edit_text(
            'درس: ' + course.field.name + '\n' +
            'استاد: ' + course.lecturer.name + '\n' +
            'گروه: ' + str(lecture.group_id) + '\n' +
            'انتخاب کنید.',
            reply_markup=keyboard
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'unsubscribe-add-lecture-(\d+)-to-student-lectures'))
    def unsubscribe_add_to_student_lectures(_, callback: CallbackQuery):
        lecture_id = callback.matches[0].group(1)
        lecture = Lecture.objects.filter(id=lecture_id).get()
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        student = user.student
        student.lectures.remove(lecture)
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'subscribe-add-lecture-(\d+)-to-student-lectures'))
    def subscribe_add_to_student_lectures(_, callback: CallbackQuery):
        lecture_id = callback.matches[0].group(1)
        lecture = Lecture.objects.filter(id=lecture_id).get()
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        student = user.student
        student.lectures.add(lecture)
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_message(filters.command('class_archives') & filters.private)
    def class_archives_start(_, message: Message):
        fields = Field.objects.all()
        message.reply_text(
            "به آرشیو کامل کلاس‌ها خوش اومدی👋🏻\n"
            "تو اینجا میتونی به اطلاعات کامل هر دوره مثل ویدیوهای ضبط شده🎥، جزوه های دست نویس📝، و لینک های مهم مثل "
            "گروه‌های هر درس🔗 دسترسی داشته باشی😎\n "
            "حتی میتونی آرشیو مارو با فایل‌هات کاملتر هم بکنی:)",
            reply_markup=InlineKeyboardMarkup(BotHandler.arrange_per_row_max([
                [
                    InlineKeyboardButton(
                        field.name,
                        callback_data='class_archives-field-' + str(field.id)
                    )
                    for field in fields
                ]
            ], 3)),
            reply_to_message_id=message.message_id
        )

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-start'))
    def class_archives_start_by_back(_, callback: CallbackQuery):
        fields = Field.objects.all()
        callback.message.edit_text(
            "به آرشیو کامل کلاس‌ها خوش اومدی👋🏻\n"
            "تو اینجا میتونی به اطلاعات کامل هر دوره مثل ویدیوهای ضبط شده🎥، جزوه های دست نویس📝، و لینک های مهم مثل "
            "گروه‌های هر درس🔗 دسترسی داشته باشی😎\n"
            "حتی میتونی آرشیو مارو با فایل‌هات کاملتر هم بکنی:)",
            reply_markup=InlineKeyboardMarkup(BotHandler.arrange_per_row_max([
                [
                    InlineKeyboardButton(
                        field.name,
                        callback_data='class_archives-field-' + str(field.id)
                    )
                    for field in fields
                ]
            ], 3))
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-field-(\d+)'))
    def class_archives_course_selection(_, callback: CallbackQuery):
        field_id = callback.matches[0].group(1)
        courses = Course.objects.filter(field_id=field_id).all()
        keyboard = BotHandler.arrange_per_row_max([
            [
                InlineKeyboardButton(
                    course.lecturer.name,
                    callback_data='class_archives-course-' + str(course.id) + '-b' + field_id
                )
                for course in courses
            ]
        ], 3)
        keyboard.append([InlineKeyboardButton(
            'بازگشت⬅️',
            callback_data='class_archives-start'
        )])
        callback.message.edit_text(
            "کدوم استاد؟🤔",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-course-(\d+)-b(\d+)'))
    def class_archives_archive_selection(_, callback: CallbackQuery):
        course_id = callback.matches[0].group(1)
        course = Course.objects.filter(id=course_id).get()
        field_id = callback.matches[0].group(2)
        keyboard = InlineKeyboard()
        keyboard.row(InlineKeyboardButton(
            'آرشیو ویدیوهای کلاس',
            callback_data='class_archives-videos-course-' + str(course.id) + '-b' + field_id
        ),
            InlineKeyboardButton(
                'آرشیو جزوات کلاس',
                callback_data='class_archives-notes-course-' + str(course.id) + '-b' + field_id
            ))
        keyboard.row(InlineKeyboardButton(
            'لینک گروه تلگرامی درس️',
            callback_data='class_archives-group_link-course-' + str(course_id) + '-b' + str(field_id)))
        keyboard.row(InlineKeyboardButton(
            'بازگشت⬅️',
            callback_data='class_archives-field-' + str(field_id)))
        callback.message.edit_text(
            "انتخاب کنید.",
            reply_markup=keyboard
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-group_link-course-(\d+)-b(\d+)'))
    def class_archives_link_view(_, callback: CallbackQuery):
        course_id = callback.matches[0].group(1)
        course = Course.objects.filter(id=course_id).get()
        field_id = callback.matches[0].group(2)
        links = GroupLink.objects.filter(course_id=course_id).all()
        if links:
            link = links[0]
            keyboard = InlineKeyboard()
            keyboard.row(InlineKeyboardButton(
                'بازگشت⬅️',
                callback_data='class_archives-course-' + str(course.id) + '-b' + str(field_id)))
            callback.message.edit_text(
                '🔹کلاس ' + course.field.name + '\n🔸استاد درس: ' + course.lecturer.name +
                '\n🔗لینک های کلاس:\n  🔹گروه تلگرام:' + '\n' + link.telegram_link + '\n',
                reply_markup=keyboard)
            callback.answer()
        else:
            callback.answer('گروهی یافت نشد!', True)

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-videos-course-(\d+)-b(\d+)'))
    def class_archives_video_session_selection(_, callback: CallbackQuery):
        course_id = callback.matches[0].group(1)
        lecture_class_sessions = LectureClassSession.objects.filter(course_id=course_id).all()
        if lecture_class_sessions:
            callback.message.edit_text("کدوم جلسه؟...",
                                       reply_markup=InlineKeyboardMarkup(BotHandler.arrange_per_row_max([
                                           [
                                               InlineKeyboardButton(
                                                   ' جلسه ' + str(lecture_class_session.session_number) + (
                                                       ' TA' if lecture_class_session.is_ta else ''),
                                                   callback_data='class_archives-videos-view-session-' + str(
                                                       lecture_class_session.id)
                                               )
                                               for lecture_class_session in lecture_class_sessions
                                           ]
                                       ], 3)),
                                       )
            callback.answer()
        else:
            callback.answer("هنوز جلسه ای موجود نیست!", True)

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-notes-course-(\d+)-b(\d+)'))
    def class_archives_note_session_selection(_, callback: CallbackQuery):
        course_id = callback.matches[0].group(1)
        lecture_class_sessions = LectureClassSession.objects.filter(course_id=course_id).all()
        if lecture_class_sessions:
            callback.message.edit_text("کدوم جلسه؟...",
                                       reply_markup=InlineKeyboardMarkup(BotHandler.arrange_per_row_max([
                                           [
                                               InlineKeyboardButton(
                                                   ' جلسه ' + str(lecture_class_session.session_number) + (
                                                       ' TA' if lecture_class_session.is_ta else ''),
                                                   callback_data='class_archives-notes-session-' + str(
                                                       lecture_class_session.id)
                                               )
                                               for lecture_class_session in lecture_class_sessions
                                           ]
                                       ], 3)),
                                       )
            callback.answer()
        else:
            callback.answer("هنوز جلسه ای موجود نیست!", True)

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-videos-view-session-(\d+)'))
    def class_archives_video_view(client: Client, callback: CallbackQuery):
        session_id = callback.matches[0].group(1)
        lecture_class_sessions = LectureClassSession.objects.filter(id=session_id).all()
        lecture_class_session = lecture_class_sessions[0]
        course = lecture_class_session.course
        videos = ClassVideo.objects.filter(lecture_class_session_id=session_id).filter(is_verified=True).all()
        keyboard = InlineKeyboard()
        if videos:
            video = videos[0]
            keyboard.row(InlineKeyboardButton(
                'بازگشت⬅️',
                callback_data='class_archives-videos-course-' + str(course.id) + '-b' + str(course.field_id)))
            try:
                chat_id = video.link.split('/')[-2]
                if chat_id.isdigit():
                    chat_id = int(chat_id)
                message_id = int(video.link.split('/')[-1])
                client.copy_message(chat_id=callback.message.chat.id, from_chat_id=chat_id, message_id=message_id)
                callback.message.reply_text(
                    '🔹ویدیوی کلاس ' + course.field.name + '\n🔸استاد درس: ' + course.lecturer.name + '\n🔹جلسه  ' + str(
                        lecture_class_session.session_number) + 'ام' + '\n🔸تاریخ  ' + str(lecture_class_session.date) +
                    '\n🔹موضوع جلسه: ' + video.subject + '\n🔸ضبط توسط: ' + video.student.first_name + ' ' +
                    video.student.last_name,
                    reply_markup=keyboard
                )
            except:
                callback.message.reply_text(
                    '🔹ویدیوی کلاس ' + course.field.name + '\n🔸استاد درس: ' + course.lecturer.name + '\n🔹جلسه  ' + str(
                        lecture_class_session.session_number) + 'ام' + '\n🔸تاریخ  ' + str(lecture_class_session.date) +
                    '\n🔹موضوع جلسه: ' + video.subject + '\n🔸ضبط توسط: ' + video.student.first_name + ' ' +
                    video.student.last_name + '\n\n' + video.link,
                    reply_markup=keyboard
                )
            callback.answer()
        else:
            keyboard.row(InlineKeyboardButton(
                'اضافه کردن ویدیوی جدید',
                callback_data='class_archives-videos-add-session-' + str(session_id)))
            keyboard.row(InlineKeyboardButton(
                'بازگشت⬅️',
                callback_data='class_archives-videos-course-' + str(course.id) + '-b' + str(course.field_id)))
            callback.message.reply_text(
                'متاسفانه ویدیویی برای این جلسه هنوز تایید نشده...',
                reply_markup=keyboard
            )
            callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-videos-add-session-(\d+)'))
    def class_archives_videos_add(_, callback: CallbackQuery):
        session_id = callback.matches[0].group(1)
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        user.state.state = BotUserState.STATES[3][0]
        user.state.data = str(session_id)
        user.state.save()
        callback.message.reply_text('فایل را در هر مکان قابل دسترسی بارگذاری کرده و فقط لینک فایل را ارسال کنید.\n'
                                    'نام شما به عنوان فرستنده جزوه نشان داده خواهد شد.'
                                    'برای انصراف از دستور /cancel استفاده کنید.',
                                    reply_to_message_id=callback.message.message_id)
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_message(filters.text & filters.private & ARCHIVE_ADD_FILE_LINK_FILTER)
    def class_archive_submit_video(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        video = ClassVideo()
        video.link = message.text
        video.student = user.student
        video.lecture_class_session = LectureClassSession.objects.filter(
            id=user.state.data).get()
        video.subject = ' - '
        video.save()
        message.reply_text('ویدیوی شما ثبت شد و بعد بازبینی و تایید برای بقیه قابل دسترسی میشه.🤓')
        BotHandler.user_state_reset(user)

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-notes-session-(\d+)'))
    def class_archives_notes_action_selection(_, callback: CallbackQuery):
        session_id = callback.matches[0].group(1)
        lecture_class_session = LectureClassSession.objects.filter(id=session_id).all()
        course = lecture_class_session[0].course
        keyboard = InlineKeyboard()
        keyboard.row(InlineKeyboardButton(
            'اضافه کردن جزوه جدید',
            callback_data='class_archives-notes-add-session-' + str(session_id)
        ),
            InlineKeyboardButton(
                'مشاهده تمام جزوه ها',
                callback_data='class_archives-notes-view-session-' + str(session_id)
            ))
        keyboard.row(InlineKeyboardButton(
            'بازگشت⬅️',
            callback_data='class_archives-notes-course-' + str(course.id) + '-b' + str(course.field_id)))
        callback.message.edit_text(
            "انتخاب کنید.",
            reply_markup=keyboard
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-notes-view-session-(\d+)'))
    def class_archives_note_selection(_, callback: CallbackQuery):
        session_id = callback.matches[0].group(1)
        lecture_class_session = LectureClassSession.objects.filter(id=session_id).first()
        notes = ClassNote.objects.filter(lecture_class_session_id=session_id).filter(is_verified=True).all()
        if notes:
            callback.message.edit_text("جزوه نوشته شده توسط کدوم یکی رو میخوای؟",
                                       reply_markup=InlineKeyboardMarkup(BotHandler.arrange_per_row_max([
                                           [
                                               InlineKeyboardButton(
                                                   note.student.first_name + ' ' + note.student.last_name,
                                                   callback_data='class_archives-note-view-session-' + str(
                                                       lecture_class_session.id) + '-b' + str(
                                                       note.id)
                                               )
                                               for note in notes
                                           ]
                                       ], 2)),
                                       )
            callback.answer()
        else:
            callback.answer('هنوز جزوه ای برای این جلسه به آرشیو اضافه نشده! در کامل کردن آرشیو سهیم باشید:)', True)

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-note-view-session-(\d+)-b(\d+)'))
    def class_archives_note_view(client: Client, callback: CallbackQuery):
        session_id = callback.matches[0].group(1)
        note_id = callback.matches[0].group(2)
        lecture_class_sessions = LectureClassSession.objects.filter(id=session_id).all()
        lecture_class_session = lecture_class_sessions[0]
        course = lecture_class_session.course
        notes = ClassNote.objects.filter(id=note_id).all()
        note = notes[0]
        keyboard = InlineKeyboard()
        keyboard.row(InlineKeyboardButton(
            'بازگشت⬅️',
            callback_data='class_archives-notes-view-session-' + str(session_id)))
        try:
            chat_id = note.link.split('/')[-2]
            if chat_id.isdigit():
                chat_id = int(chat_id)
            message_id = int(note.link.split('/')[-1])
            client.copy_message(chat_id=callback.message.chat.id, from_chat_id=chat_id, message_id=message_id)
            callback.message.reply_text(
                '🔹جزوه کلاس ' + course.field.name + '\n🔸استاد درس: ' + course.lecturer.name + '\n🔹جلسه  ' + str(
                    lecture_class_session.session_number) + 'ام\n🔸تاریخ  ' + str(
                    lecture_class_session.date) + '\n🔹موضوع جلسه: ' + note.subject + '\n🔸نوشته شده توسط: ' +
                note.student.first_name + ' ' + note.student.last_name,
                reply_markup=keyboard
            )
        except:
            callback.message.reply_text(
                '🔹جزوه کلاس ' + course.field.name + '\n🔸استاد درس: ' + course.lecturer.name + '\n🔹جلسه  ' + str(
                    lecture_class_session.session_number) + 'ام\n🔸تاریخ  ' + str(
                    lecture_class_session.date) + '\n🔹موضوع جلسه: ' + note.subject + '\n🔸نوشته شده توسط: ' +
                note.student.first_name + ' ' + note.student.last_name + '\n\n' + note.link,
                reply_markup=keyboard
            )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'class_archives-notes-add-session-(\d+)'))
    def class_archive_add_note(_, callback: CallbackQuery):
        session_id = callback.matches[0].group(1)
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        user.state.state = BotUserState.STATES[3][0]
        user.state.data = str(session_id)
        user.state.save()
        callback.message.reply_text('فایل را در هر مکان قابل دسترسی بارگذاری کرده و فقط لینک فایل را ارسال کنید.\n'
                                    'نام شما به عنوان فرستنده جزوه نشان داده خواهد شد.'
                                    'برای انصراف از دستور /cancel استفاده کنید.',
                                    reply_to_message_id=callback.message.message_id)
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_message(filters.text & filters.private & ARCHIVE_ADD_FILE_LINK_FILTER)
    def class_archive_submit_note(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        note = ClassNote()
        note.link = message.text
        note.student = user.student
        note.lecture_class_session = LectureClassSession.objects.filter(
            id=user.state.data).get()
        note.subject = ' - '
        note.save()
        message.reply_text('جزوتون ثبت شد و بعد بازبینی و تایید برای بقیه قابل دسترسی میشه.🤓')
        BotHandler.user_state_reset(user)

    @staticmethod
    @connection_check()
    @app.on_message(filters.command('feedback') & filters.private)
    def feedback_start(_, message: Message):
        fields = Field.objects.all()
        message.reply_text(
            'یکی از درسای زیر رو انتخاب کن تا ببینم چیا بهم گفتن راجبش.👨💻',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                'مشاهده بازخورد های تمام دروس من در سامانه ترم‌ایناتور',
                callback_data='feedback-terminator'
            )]] + BotHandler.arrange_per_row_max([
                [
                    InlineKeyboardButton(
                        field.name,
                        callback_data='feedback-field-' + str(field.id)
                    )
                    for field in fields
                ]
            ], 3)),
            reply_to_message_id=message.message_id
        )

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'feedback-start'))
    def feedback_start_by_back(_, callback: CallbackQuery):
        fields = Field.objects.all()
        callback.message.edit_text(
            'یکی از درسای زیر رو انتخاب کن تا ببینم چیا بهم گفتن راجبش.👨‍💻',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                'مشاهده بازخورد های تمام دروس من در سامانه ترم‌ایناتور',
                callback_data='feedback-terminator'
            )]] + BotHandler.arrange_per_row_max([
                [
                    InlineKeyboardButton(
                        field.name,
                        callback_data='feedback-field-' + str(field.id)
                    )
                    for field in fields
                ]
            ], 3))
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'feedback-terminator'))
    def feedback_terminator(_, callback: CallbackQuery):
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        student_id = str(user.student.student_id)
        match = re.match(r'\d{8}', student_id)
        if not match:
            callback.answer('ابتدا باید شماره دانشجویی خود را در بخش احراز هویت وارد نمایید.')
            return
        session = requests.Session()
        BotHandler.login_session(session, student_id)
        text = session.get('http://term.inator.ir/schedule/summary/').text
        soup = BeautifulSoup(text, features="html.parser")
        rows = soup.table.find_all('tr')
        buttons = []
        for row in rows:
            if row.get('id'):
                match = re.match(r'course-(\d{5})-(\d{1,2})', row['id'])
                if match:
                    field_id = match.group(1)
                    group_id = match.group(2)
                    lecture = Lecture.objects.filter(group_id=group_id).filter(course__field__id=field_id).first()
                    if lecture:
                        buttons.append([
                            InlineKeyboardButton(lecture.course.field.name + ' - ' + lecture.course.lecturer.name,
                                                 callback_data='feedback-course-' + str(
                                                     lecture.course.id) + '-b' + field_id)])
        if not buttons:
            callback.answer('لیست دروس ترم‌ایناتور شما خالیست.')
            return
        callback.message.edit_text('یکی از درسای زیر رو انتخاب کن تا ببینم چیا بهم گفتن راجبش.👨‍💻',
                                   reply_markup=InlineKeyboardMarkup(buttons))
        callback.answer()

    @staticmethod
    def login_session(site_session, student_id):
        text = site_session.get('http://term.inator.ir/login/?next=/').text
        soup = BeautifulSoup(text, features="html.parser")
        inputs = soup.form.find_all('input')
        data = {'student-id': student_id}
        for text_input in inputs:
            if text_input.get('name') == 'csrfmiddlewaretoken':
                data['csrfmiddlewaretoken'] = text_input['value']
                break
        site_session.post('http://term.inator.ir/login/?next=/', data,
                          cookies={'csrftoken': data['csrfmiddlewaretoken']})

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'feedback-field-(\d+)'))
    def feedback_course_selection(_, callback: CallbackQuery):
        field_id = callback.matches[0].group(1)
        courses = Course.objects.filter(field_id=field_id).all()
        keyboard = BotHandler.arrange_per_row_max([
            [
                InlineKeyboardButton(
                    course.lecturer.name,
                    callback_data='feedback-course-' + str(course.id) + '-b' + field_id
                )
                for course in courses
            ]
        ], 3)
        keyboard.append([InlineKeyboardButton(
            'بازگشت⬅️',
            callback_data='feedback-start'
        )])
        callback.message.edit_text(
            'درس: ' + Field.objects.filter(id=field_id).get().name + '\n' +
            'کدوم استاد؟🤔',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'feedback-course-(\d+)-b(\d+)'))
    def feedback_lecturer_selection(_, callback: CallbackQuery):
        course_id = callback.matches[0].group(1)
        course = Course.objects.filter(id=course_id).get()
        field_id = callback.matches[0].group(2)
        keyboard = InlineKeyboard()
        keyboard.row(InlineKeyboardButton(
            'مشاهده تجربه بقیه',
            callback_data='feedback-view-' + str(course.id) + '-p-1-b' + field_id
        ),
            InlineKeyboardButton(
                'ثبت تجربه',
                callback_data='feedback-course-submit-' + str(course.id)
            ))
        keyboard.row(InlineKeyboardButton(
            'بازگشت⬅️',
            callback_data='feedback-field-' + field_id))
        text = BotHandler.session.get('http://term.inator.ir/courses/info/' + field_id + '/').text
        soup = BeautifulSoup(text, features="html.parser")
        tds = soup.tbody.find_all("td")
        total_capacity = 0
        terminator_capacity_filled = 0
        for lecture in course.lecture_set.all():
            for i in range(0, len(tds), 5):
                if tds[i].string == str(lecture.group_id):
                    total_capacity += int(tds[i + 3].string)
                    terminator_capacity_filled += int(tds[i + 4].string)
        callback.message.edit_text(
            'درس: ' + course.field.name + '\n' +
            'استاد: ' + course.lecturer.name + '\n' +
            'ظرفیت درس: ' + str(total_capacity) + '\n' +
            'ثبت‌نامی در ترم‌ایناتور: ' + str(terminator_capacity_filled) + '\n' +
            'انتخاب کنید.',
            reply_markup=keyboard
        )
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'feedback-view-(\d+)-p-(\d+)-b(\d+)'))
    def feedbacks_view(_, callback: CallbackQuery):
        course = Course.objects.filter(id=callback.matches[0].group(1)).get()
        page = int(callback.matches[0].group(2))
        field_id = callback.matches[0].group(3)
        feedbacks = Feedback.objects.filter(course_id=course.id).filter(is_verified=True).annotate(
            num_likes=Count('feedbacklike')).order_by('-num_likes').all()
        if feedbacks:
            feedback = feedbacks[page - 1]
            keyboard = InlineKeyboard(row_width=3)
            keyboard.paginate(len(feedbacks), page, 'feedback-view-' + str(course.id) + '-p-{number}-b' + field_id)
            keyboard.row(InlineKeyboardButton(
                str(feedback.feedbacklike_set.count()) + '👌🏿' if feedback.feedbacklike_set else '' + '👌🏿',
                'feedback-like-' + str(feedback.id) + '-b' + field_id))
            keyboard.row(InlineKeyboardButton(
                'بازگشت⬅️',
                callback_data='feedback-field-' + field_id))
            callback.message.edit_text(
                feedback.text,
                reply_markup=keyboard
            )
            callback.answer()
        else:
            callback.answer('هنوز هیچکس نظری برای این استاد ثبت نکرده😬'
                            'اگه تجربه‌ای دارید با ثبتش به ما و بقیه دانشجو‌ها کمک کنید', True)

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'feedback-like-(\d+)-b(\d+)'))
    def feedback_like(_, callback: CallbackQuery):
        feedback = Feedback.objects.filter(id=callback.matches[0].group(1)).filter(is_verified=True).get()
        feedbacks = Feedback.objects.filter(course_id=feedback.course.id).filter(is_verified=True).annotate(
            num_likes=Count('feedbacklike')).order_by('-num_likes').all()
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        like = feedback.feedbacklike_set.filter(student=user.student).first()
        field_id = callback.matches[0].group(2)
        keyboard = InlineKeyboard(row_width=3)
        keyboard.paginate(len(feedbacks), list(feedbacks).index(feedback) + 1,
                          'feedback-view-' + str(feedback.course.id) + '-p-{number}')
        keyboard.row(InlineKeyboardButton(
            str(feedback.feedbacklike_set.count() + (
                -1 if like else 1)) + '👌🏿' if feedback.feedbacklike_set else '' + '👌🏿',
            'feedback-like-' + str(feedback.id)))
        keyboard.row(InlineKeyboardButton(
            'بازگشت⬅️',
            callback_data='feedback-field-' + field_id))
        if feedback:
            if not like:
                FeedbackLike.objects.create(feedback=feedback, student=user.student)
                callback.answer('شما با این نظر حال کردین.')
                callback.message.edit_reply_markup(keyboard)
            else:
                like.delete()
                callback.answer('تاییدتون برداشته شد.')
                callback.message.edit_reply_markup(keyboard)

    @staticmethod
    @connection_check()
    @app.on_callback_query(filters.regex(r'feedback-course-submit-(\d+)'))
    def feedback_submit_state_set(_, callback: CallbackQuery):
        course = Course.objects.filter(id=callback.matches[0].group(1)).get()
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        user.state.state = BotUserState.STATES[1][0]
        user.state.data = str(course.id)
        user.state.save()
        callback.message.reply_text('نظرتونو به صورت متنی وارد کنید.'
                                    'برای انصراف از دستور /cancel استفاده کنید.',
                                    reply_to_message_id=callback.message.message_id)
        callback.answer()

    @staticmethod
    @connection_check()
    @app.on_message(filters.text & filters.private & FEEDBACK_SUBMIT_FILTER)
    def feedback_submit(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        feedback = Feedback()
        feedback.text = message.text
        feedback.course = Course.objects.filter(id=user.state.data).get()
        feedback.student = user.student
        feedback.save()
        message.reply_text('نظرتون ثبت شد و بعد بازبینی و تایید برای بقیه قابل دیدن میشه.🤓')
        BotHandler.user_state_reset(user)

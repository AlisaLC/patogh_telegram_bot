import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from pykeyboard import InlineKeyboard
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

from courses.models import Field, Course
from feedbacks.models import Feedback, FeedbackLike
from students.models import Student
from telegram_bot.models import BotUser, BotUserState


class Command(BaseCommand):

    def handle(self, *args, **options):
        BotHandler(self)


class BotHandler:
    app = Client('patogh_bot', bot_token=settings.BOT_TOKEN, api_id=settings.BOT_API_ID, api_hash=settings.BOT_API_HASH)

    def __init__(self, command):
        self.command = command
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

    @staticmethod
    def arrange_per_row_max(matrix: list[list[InlineKeyboardButton]], n: int) -> list[list[InlineKeyboardButton]]:
        output = []
        for rows in matrix:
            for item in rows:
                if output:
                    if len(output[-1]) < n:
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
    @app.on_message(filters.command('cancel') & filters.private)
    def user_cancel(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        BotHandler.user_state_reset(user)
        message.reply_text('درخواست شما لغو شد.')

    @staticmethod
    @app.on_message(filters.command('authorize') & filters.private)
    def user_authorize(_, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        message.reply_text('نام کوچک خود را وارد کنید.')
        user.state.state = BotUserState.STATES[2][0]
        user.state.data = 'FIRST_NAME'
        user.state.save()

    @staticmethod
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
    @app.on_message(filters.command('feedback') & filters.private)
    def feedback_start(_, message: Message):
        fields = Field.objects.all()
        message.reply_text(
            'یکی از درسای زیر رو انتخاب کن تا ببینم چیا بهم گفتن راجبش.👨💻',
            reply_markup=InlineKeyboardMarkup(BotHandler.arrange_per_row_max([
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
    @app.on_callback_query(filters.regex(r'feedback-start'))
    def feedback_start_by_back(_, callback: CallbackQuery):
        fields = Field.objects.all()
        callback.message.edit_text(
            'یکی از درسای زیر رو انتخاب کن تا ببینم چیا بهم گفتن راجبش.👨‍💻',
            reply_markup=InlineKeyboardMarkup(BotHandler.arrange_per_row_max([
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
        session = requests.Session()
        text = session.get('http://term.inator.ir/courses/info/' + field_id + '/',
                           cookies={'sessionid': settings.SESSION_ID}).text
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
                            'اگه تجربه‌ای دارید با ثبتش به ما و بقیه دانشجو‌ها کمک کنید'
                            , True)

    @staticmethod
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

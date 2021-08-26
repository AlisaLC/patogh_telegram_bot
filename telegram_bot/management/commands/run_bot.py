from django.conf import settings
from django.core.management.base import BaseCommand
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

from courses.models import Field, Course
from feedbacks.models import Feedback
from students.models import Student
from telegram_bot.models import BotUser, BotUserState


class Command(BaseCommand):

    def handle(self, *args, **options):
        BotHandler()


class BotHandler:
    app = Client('patogh_bot', bot_token=settings.BOT_TOKEN, api_id=settings.BOT_API_ID, api_hash=settings.BOT_API_HASH)

    def __init__(self, command):
        self.app.run()

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
    def state_filter(filter_args, client, message) -> bool:
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        if filter_args.data != '':
            return filter_args.state == user.state.state and filter_args.data == user.state.data
        return filter_args.state == user.state.state

    @staticmethod
    @app.on_message(filters.text & filters.private & filters.create(state_filter, None, state=BotUserState.STATES[2],
                                                                    data='FIRST_NAME'))
    def authorization_first_name(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        user.student.first_name = message.text
        user.state.data = 'LAST_NAME'
        user.save()
        message.reply_text('نام خانوادگی خود را وارد کنید.')

    @staticmethod
    @app.on_message(filters.text & filters.private & filters.create(state_filter, None, state=BotUserState.STATES[2],
                                                                    data='LAST_NAME'))
    def authorization_last_name(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        user.student.last_name = message.text
        user.state.data = 'STUDENT_ID'
        user.save()
        message.reply_text('شماره دانشجویی خود را وارد کنید.')

    @staticmethod
    @app.on_message(filters.text & filters.private & filters.create(state_filter, None, state=BotUserState.STATES[2],
                                                                    data='STUDENT_ID'))
    def authorization_student_id(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        user.student.student_id = message.text
        user.state.state = BotUserState.STATES[0]
        user.state.data = ''
        user.save()
        message.reply_text('با موفقیت احراز هویت شدید. هویت شما کاملاً محفوظ است و تنها برای اطلاع رسانی به شما مورد '
                           'استفاده قرار خواهد گرفت.')

    @staticmethod
    @app.on_message(filters.command('start') & filters.private)
    def user_start(client: Client, message: Message):
        user = BotUser.objects.create(user_id=message.from_user.id, chat_id=message.chat.id)
        user.save()
        state = BotUserState.objects.create()
        state.state = BotUserState.STATES[0]
        state.save()
        user.state = state
        user.save()
        message.reply_text('دانشجوی گرامی لطفاً هر چه زودتر هویت خود را از طریق دستور /authorize احراز نمایید.')

    @staticmethod
    @app.on_message(filters.command('cancel') & filters.private)
    def user_cancel(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        user.state.state = BotUserState.STATES[0]
        user.state.data = ''
        user.save()
        message.reply_text('درخواست شما لغو شد.')

    @staticmethod
    @app.on_message(filters.command('authorize') & filters.private)
    def user_authorize(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        if not user.student:
            student = Student.objects.create()
            student.save()
            user.student = student
            user.save()
        message.reply_text('نام کوچک خود را وارد کنید.')
        user.state.state = BotUserState.STATES[2]
        user.state.data = 'FIRST_NAME'
        user.save()

    @staticmethod
    @app.on_message(filters.command('feedback') & filters.private)
    def feedback_start(client: Client, message: Message):
        fields = Field.objects.all()
        message.reply_text(
            "درس مورد نظر را انتخاب کنید.",
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
    @app.on_callback_query(filters.regex(r'feedback-field-(\d+)'))
    def feedback_course_selection(client: Client, callback: CallbackQuery):
        courses = Course.objects.filter(field_id=callback.matches[0].group(1)).all()
        callback.message.reply_text(
            "استاد مورد نظر را انتخاب کنید.",
            reply_markup=InlineKeyboardMarkup(BotHandler.arrange_per_row_max([
                [
                    InlineKeyboardButton(
                        course.lecturer.name,
                        callback_data='feedback-course-' + str(course.id)
                    )
                    for course in courses
                ]
            ], 3)),
            reply_to_message_id=callback.message.message_id
        )

    @staticmethod
    @app.on_callback_query(filters.regex(r'feedback-course-(\d+)'))
    def feedback_lecturer_selection(client: Client, callback: CallbackQuery):
        course = Course.objects.filter(id=callback.matches[0].group(1)).get()
        callback.message.reply_text(
            "انتخاب کنید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        'مشاهده تمامی نظرات',
                        callback_data='feedback-course-view-' + str(course.id)
                    ),
                    InlineKeyboardButton(
                        'ثبت نظر',
                        callback_data='feedback-course-submit-' + str(course.id)
                    )
                ]
            ]),
            reply_to_message_id=callback.message.message_id
        )

    @staticmethod
    @app.on_callback_query(filters.regex(r'feedback-course-view-(\d+)'))
    def feedbacks_view(client: Client, callback: CallbackQuery):
        course = Course.objects.filter(id=callback.matches[0].group(1)).get()
        feedbacks = Feedback.objects.filter(course_id=course.id).filter(is_verified=True).all()
        if feedbacks:
            for feedback in feedbacks:
                callback.message.reply_text(
                    feedback.text,
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton(
                                str(feedback.feedbacklike_set.count()) + '👌🏿',
                                callback_data='feedback-like-' + str(feedback.id)
                            )
                        ]
                    ]),
                    reply_to_message_id=callback.message.message_id
                )

    @staticmethod
    @app.on_callback_query(filters.regex(r'feedback-like-(\d+)'))
    def feedback_like(client: Client, callback: CallbackQuery):
        feedback = Feedback.objects.filter(id=callback.matches[0].group(1)).filter(is_verified=True).get()
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        if feedback:
            feedback.feedbacklike_set.append(user.student)
            feedback.save()

    @staticmethod
    @app.on_callback_query(filters.regex(r'feedback-course-submit-(\d+)'))
    def feedback_submit_state_set(client: Client, callback: CallbackQuery):
        course = Course.objects.filter(id=callback.matches[0].group(1)).get()
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        user.state.state = BotUserState.STATES[1]
        user.state.data = str(course.id)
        user.save()
        callback.message.reply_text('نظر خود را به صورت متنی وارد کنید.'
                                    'برای انصراف از دستور /cancel استفاده کنید.',
                                    reply_to_message_id=callback.message.message_id)

    @staticmethod
    @app.on_message(filters.text & filters.private & filters.create(state_filter, None, state=BotUserState.STATES[1],
                                                                    data=''))
    def feedback_submit(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        feedback = Feedback.objects.create()
        feedback.text = message.text
        feedback.save()
        feedback.course = Course.objects.filter(id=user.state.data).get()
        feedback.student = user.student
        feedback.save()
        message.reply_text('نظر شما ثبت شد و در انتظار تایید قرار گرفت.')
        user.state.state = BotUserState.STATES[0]
        user.state.data = ''
        user.save()

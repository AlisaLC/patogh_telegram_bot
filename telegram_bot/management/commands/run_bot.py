from django.conf import settings
from django.core.management.base import BaseCommand
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

from courses.models import Field, Course
from students.models import Student
from telegram_bot.models import BotUser, BotUserState


class Command(BaseCommand):

    def handle(self, *args, **options):
        BotHandler(self)


class BotHandler:
    app = Client('patogh_bot', bot_token=settings.BOT_TOKEN, api_id=settings.BOT_API_ID, api_hash=settings.BOT_API_HASH)
    command = None

    def __init__(self, command):
        self.app.run()
        self.command = command

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
    @app.on_message(filters.command('authorize') & filters.private)
    def user_start(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        if not user.student:
            student = Student.objects.create()
            student.save()
            user.student = student
            user.save()
        message.reply_text('نام کوچک خود را وارد کنید.')
        state = BotUserState.objects.create()
        state.state = BotUserState.STATES[2]
        state.data = 'FIRST_NAME'
        state.save()
        user.states = state
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
                        callback_data='feedback-view-' + str(course.id)
                    ),
                    InlineKeyboardButton(
                        'ثبت نظر',
                        callback_data='feedback-submit-' + str(course.id)
                    )
                ]
            ]),
            reply_to_message_id=callback.message.message_id
        )

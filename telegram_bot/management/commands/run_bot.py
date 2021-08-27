from django.conf import settings
from django.core.management.base import BaseCommand
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

from courses.models import Field, Course
from feedbacks.models import Feedback, FeedbackLike
from students.models import Student
from telegram_bot.models import BotUser, BotUserState
from pykeyboard import InlineKeyboard


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
    def user_start(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).first()
        if user:
            user.chat_id = message.chat.id
            user.save()
        else:
            user = BotUser(user_id=message.from_user.id, chat_id=message.chat.id)
            state = BotUserState.objects.create(state=BotUserState.STATES[0][0], data='')
            user.state = state
            student = Student.objects.create()
            user.student = student
            user.save()
            message.reply_text('دانشجوی گرامی لطفاً هر چه زودتر هویت خود را از طریق دستور /authorize احراز نمایید.')

    @staticmethod
    @app.on_message(filters.command('cancel') & filters.private)
    def user_cancel(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        BotHandler.user_state_reset(user)
        message.reply_text('درخواست شما لغو شد.')

    @staticmethod
    @app.on_message(filters.command('authorize') & filters.private)
    def user_authorize(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        message.reply_text('نام کوچک خود را وارد کنید.')
        user.state.state = BotUserState.STATES[2][0]
        user.state.data = 'FIRST_NAME'
        user.state.save()

    @staticmethod
    @app.on_message(
        filters.text & filters.private & AUTHORIZATION_FIRST_NAME_FILTER)
    def authorization_first_name(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        user.student.first_name = message.text
        user.student.save()
        user.state.data = 'LAST_NAME'
        user.state.save()
        message.reply_text('نام خانوادگی خود را وارد کنید.')

    @staticmethod
    @app.on_message(
        filters.text & filters.private & AUTHORIZATION_LAST_NAME_FILTER)
    def authorization_last_name(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        user.student.last_name = message.text
        user.student.save()
        user.state.data = 'STUDENT_ID'
        user.state.save()
        message.reply_text('شماره دانشجویی خود را وارد کنید.')

    @staticmethod
    @app.on_message(
        filters.text & filters.private & AUTHORIZATION_STUDENT_ID_FILTER)
    def authorization_student_id(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        user.student.student_id = message.text
        user.student.save()
        BotHandler.user_state_reset(user)
        message.reply_text('با موفقیت احراز هویت شدید. هویت شما کاملاً محفوظ است و تنها برای اطلاع رسانی به شما مورد '
                           'استفاده قرار خواهد گرفت.')

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
                        callback_data='feedback-view-' + str(course.id) + '-p-1'
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
    @app.on_callback_query(filters.regex(r'feedback-view-(\d+)-p-(\d+)'))
    def feedbacks_view(client: Client, callback: CallbackQuery):
        course = Course.objects.filter(id=callback.matches[0].group(1)).get()
        page = int(callback.matches[0].group(2))
        feedbacks = Feedback.objects.filter(course_id=course.id).filter(is_verified=True).all()
        if feedbacks:
            feedback = feedbacks[page - 1]
            keyboard = InlineKeyboard(row_width=3)
            keyboard.paginate(len(feedbacks), page, 'feedback-view-' + str(course.id) + '-p-{number}')
            keyboard.row(InlineKeyboardButton(
                str(feedback.feedbacklike_set.count()) + '👌🏿' if feedback.feedbacklike_set else '' + '👌🏿',
                'feedback-like-' + str(feedback.id)))
            callback.message.edit_text(
                feedback.text,
                reply_markup=keyboard
            )

    @staticmethod
    @app.on_callback_query(filters.regex(r'feedback-like-(\d+)'))
    def feedback_like(client: Client, callback: CallbackQuery):

        feedback = Feedback.objects.filter(id=callback.matches[0].group(1)).filter(is_verified=True).get()
        feedbacks = Feedback.objects.filter(course_id=feedback.course.id).filter(is_verified=True).all()
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        like = feedback.feedbacklike_set.filter(student=user.student).first()
        keyboard = InlineKeyboard(row_width=3)
        keyboard.paginate(len(feedbacks), list(feedbacks).index(feedback) + 1, 'feedback-view-' + str(feedback.course.id) + '-p-{number}')
        keyboard.row(InlineKeyboardButton(
            str(feedback.feedbacklike_set.count() + (-1 if like else 1)) + '👌🏿' if feedback.feedbacklike_set else '' + '👌🏿',
            'feedback-like-' + str(feedback.id)))
        if feedback:
            if not like:
                FeedbackLike.objects.create(feedback=feedback, student=user.student)
                callback.answer('شما این نظر را تایید کردید.')
                callback.message.edit_reply_markup(keyboard)
            else:
                like.delete()
                callback.answer('شما موافقت خود را با این نظر پس گرفتید.')
                callback.message.edit_reply_markup(keyboard)

    @staticmethod
    @app.on_callback_query(filters.regex(r'feedback-course-submit-(\d+)'))
    def feedback_submit_state_set(client: Client, callback: CallbackQuery):
        course = Course.objects.filter(id=callback.matches[0].group(1)).get()
        user = BotUser.objects.filter(chat_id=callback.message.chat.id).get()
        user.state.state = BotUserState.STATES[1][0]
        user.state.data = str(course.id)
        user.state.save()
        callback.message.reply_text('نظر خود را به صورت متنی وارد کنید.'
                                    'برای انصراف از دستور /cancel استفاده کنید.',
                                    reply_to_message_id=callback.message.message_id)

    @staticmethod
    @app.on_message(filters.text & filters.private & FEEDBACK_SUBMIT_FILTER)
    def feedback_submit(client: Client, message: Message):
        user = BotUser.objects.filter(user_id=message.from_user.id).get()
        feedback = Feedback()
        feedback.text = message.text
        feedback.course = Course.objects.filter(id=user.state.data).get()
        feedback.student = user.student
        feedback.save()
        message.reply_text('نظر شما ثبت شد و در انتظار تایید قرار گرفت.')
        BotHandler.user_state_reset(user)

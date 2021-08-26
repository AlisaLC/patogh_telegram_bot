from django.db import models

from students.models import Student


class BotUser(models.Model):
    user_id = models.IntegerField()
    chat_id = models.IntegerField()
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.user_id) + str(self.student) if self.student else None


class BotUserState(models.Model):
    STATES = ((0, 'None'),
              (1, 'Giving Feedback'),
              (2, 'Authorizing'))

    state = models.IntegerField(choices=STATES)
    data = models.TextField()
    user = models.OneToOneField(BotUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.STATES[self.state]

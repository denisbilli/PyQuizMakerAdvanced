import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone


def user_directory_path(instance, filename):
    # This will convert the username to lowercase
    # and will replace spaces with underscores
    username = slugify(instance.user.username.lower())
    return f'{username}/test_{timezone.now().strftime("%Y%m%d")}/{filename}'


class Test(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    enabled = models.BooleanField(default=False)
    is_graded = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Exercise(models.Model):
    TYPE_CHOICES = [
        ('O', 'Domanda aperta'),
        ('M', 'Scelta multipla'),
        ('C', 'Codice'),
        ('D', 'Diagramma di flusso'),
    ]

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='exercises')
    title = models.CharField(max_length=255)
    description = models.TextField()
    score = models.PositiveIntegerField(null=True, blank=True)
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, blank=True, null=True)
    expected_answer = models.TextField(null=True, blank=True)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class UserExercise(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    signed = models.BooleanField(default=False)

    class Meta:
        unique_together = (('user', 'exercise'),)


class Choice(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='choices', blank=True, null=True)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True, null=True)
    answer_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, blank=True, null=True)
    file = models.FileField(upload_to=user_directory_path, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s submission for {self.exercise.title}"



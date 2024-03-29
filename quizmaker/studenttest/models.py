import datetime

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


def user_directory_path(instance, filename):
    # This will convert the username to lowercase
    # and will replace spaces with underscores
    username = slugify(instance.user.username.lower())
    return f'{username}/test_{timezone.now().strftime("%Y%m%d")}/{filename}'


class Course(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    enabled = models.BooleanField(default=True)
    visible_to = models.ManyToManyField(User, blank=True, related_name='visible_courses')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def is_student_enrolled(self, user):
        """ Controlla se l'utente è iscritto al corso. """
        return Enrollment.objects.filter(student=user, course=self).exists()

    def __str__(self):
        return self.name


class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrollment_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'course']

    def __str__(self):
        return f"{self.student.name} - {self.course.name}"


class Test(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    enabled = models.BooleanField(default=False)
    is_graded = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    visible_to = models.ManyToManyField(User, blank=True, related_name='visible_tests')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Exercise(models.Model):
    TYPE_CHOICES = [
        ('O', _('Domanda aperta')),
        ('M', _('Scelta multipla')),
        ('C', _('Codice')),
        ('D', _('Diagramma di flusso')),
    ]

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='exercises')
    title = models.CharField(max_length=255)
    description = models.TextField()
    score = models.PositiveIntegerField(null=True, blank=True)
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, blank=True, null=True)
    expected_answer = models.TextField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class UserExercise(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    signed = models.BooleanField(default=False)
    stars = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(5)])

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



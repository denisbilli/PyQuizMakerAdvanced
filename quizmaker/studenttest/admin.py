# myapp/admin.py

import copy

from django.urls import path
from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import *

from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import User


class ExerciseInline(admin.StackedInline):  # This allows you to add/edit Exercises directly from the Test admin page.
    model = Exercise
    extra = 1  # Number of extra empty forms


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('title', 'test', 'type', 'enabled', 'score', 'duplicate_link')
    list_filter = ['test', 'type']
    search_fields = ['title']

    def duplicate_link(self, obj):
        return format_html('<a href="{}">Duplicate</a>', reverse('duplicate_exercise', args=[obj.pk]))

    duplicate_link.short_description = 'Duplicate Exercise'


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'enabled', 'is_graded', 'due_date', 'users_per_test')
    list_filter = ['is_graded']
    search_fields = ['name', 'description']
    filter_horizontal = ('visible_to',)
    # inlines = [ExerciseInline]  # Add the inline to the admin
    actions = ['duplicate_test', ]

    def duplicate_test(self, request, queryset):
        for test in queryset:
            try:
                print(f'Test {test.id} has {test.exercises.count()} exercises')
                with transaction.atomic():
                    # Duplicate the test
                    test_copy = copy.deepcopy(test)
                    test_copy.pk = None
                    test_copy.enabled = False
                    test_copy.save()

                    # Duplicate the exercises
                    exercises = Exercise.objects.filter(test=test)
                    print(f'Found {test.exercises.count()} exercises to duplicate')
                    for exercise in exercises:
                        new_exercise = copy.deepcopy(exercise)
                        new_exercise.pk = None
                        new_exercise.enabled = False
                        new_exercise.test = test_copy
                        new_exercise.save()
            except Exception as e:
                self.message_user(request, f'Error duplicating test {test.id}: {str(e)}', messages.ERROR)

    duplicate_test.short_description = 'Duplicate Test'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/users/',
                self.admin_site.admin_view(UsersPerTestView.as_view()),
                name='users_per_test',
            ),
        ]
        return custom_urls + urls

    def users_per_test(self, obj):
        url = reverse("admin:users_per_test", args=[obj.id])
        return format_html(f'<a href="{url}">Users per Test</a>')
    users_per_test.short_description = 'Users per Test'


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'answer_text', 'answer_choice')
    list_filter = ['user', 'exercise']
    search_fields = ['user__username', 'exercise__title']


@method_decorator(staff_member_required, name='dispatch')
class UsersPerTestView(PermissionRequiredMixin, DetailView):
    model = Test
    template_name = "admin/studenttest/users_per_test.html"  # replace "your_app_name" with your app name
    permission_required = "studenttest.view_test"  # replace "your_app_name" with your app name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        test = context['object']

        users_with_submissions = User.objects.filter(submission__exercise__test=test).distinct()
        user_submissions = {user: user.submission_set.filter(exercise__test=test) for user in users_with_submissions}

        context.update({
            **admin.site.each_context(self.request),
            'opts': self.model._meta,
            'user_submissions': user_submissions,
        })

        return context


@admin.register(UserExercise)
class UserExerciseAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'signed')
    list_filter = ('user', 'exercise__test',)
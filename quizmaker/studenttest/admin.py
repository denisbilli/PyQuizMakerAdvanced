# myapp/admin.py

import copy

from django.contrib.admin import helpers, SimpleListFilter
from django.template.response import TemplateResponse
from django.urls import path
from django.contrib import admin, messages
from django.shortcuts import render
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect
from django.db import transaction

from .forms import AssignTestsToCourseForm
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


# region FILTRI PERSONALIZZATI BASATI SULL'UTENTE CREATORE

class UserCourseFilter(SimpleListFilter):
    title = 'course'  # o il titolo appropriato
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        # Qui, restituisci solo i corsi creati dall'utente
        if request.user.is_superuser:
            courses = Course.objects.all()
        else:
            courses = Course.objects.filter(creator=request.user)
        return [(c.id, c.name) for c in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(course__id=self.value())
        return queryset


class UserTestFilter(SimpleListFilter):
    title = 'test'  # o il titolo appropriato
    parameter_name = 'test'

    def lookups(self, request, model_admin):
        # Qui, restituisci solo i corsi creati dall'utente
        if request.user.is_superuser:
            tests = Test.objects.all()
        else:
            tests = Test.objects.filter(creator=request.user)
        return [(t.id, t.name) for t in tests]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(course__id=self.value())
        return queryset

# endregion

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'enabled')  # Adjust these fields based on your Course model
    list_filter = ('enabled',)  # Filters for easier searching
    search_fields = ('name',)  # Fields to search

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)

    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.creator != request.user:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.creator != request.user:
            return False
        return True


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrollment_date')  # Campi da mostrare nell'elenco
    list_filter = (UserCourseFilter, 'enrollment_date')  # Filtri per facilitare la ricerca
    search_fields = ('student__username', 'course__name')  # Campi di ricerca

    # Opzionale: Personalizzazione del form di modifica
    # fields = ['student', 'course', 'enrollment_date']  # Campi da mostrare nel form di modifica
    # readonly_fields = ('enrollment_date',)  # Campi di sola lettura
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(course__creator=request.user)

    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser:
            return obj.course.creator == request.user
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser:
            return obj.course.creator == request.user
        return True


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('title', 'test', 'type', 'enabled', 'score', 'duplicate_link')
    list_filter = [UserTestFilter, 'type']
    search_fields = ['title']

    def duplicate_link(self, obj):
        return format_html('<a href="{}">Duplicate</a>', reverse('duplicate_exercise', args=[obj.pk]))

    duplicate_link.short_description = 'Duplicate Exercise'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)

    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.creator != request.user:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.creator != request.user:
            return False
        return True


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'enabled', 'is_graded', 'due_date', 'course', 'users_per_test')
    list_filter = ['is_graded']
    search_fields = ['name', 'description']
    filter_horizontal = ('visible_to',)
    # inlines = [ExerciseInline]  # Add the inline to the admin
    actions = ['duplicate_test', 'assign_tests_to_course']

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

    @admin.action(description='Assign tests to a course')
    def assign_tests_to_course(self, request, queryset):
        print(request.POST)
        if 'apply' in request.POST:
            form = AssignTestsToCourseForm(request.POST)
            if form.is_valid():
                course = form.cleaned_data['course']
                selected_ids = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
                Test.objects.filter(id__in=selected_ids).update(course=course)
                self.message_user(request, "Tests assigned to course successfully.", messages.SUCCESS)
                return HttpResponseRedirect(request.get_full_path())
            else:
                self.message_user(request, "Form is not valid.", messages.ERROR)

        form = AssignTestsToCourseForm()
        context = {
            'form': form,
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        }
        return render(request, 'admin/assign_tests_to_course.html', context)

    duplicate_test.short_description = 'Duplicate Test'
    users_per_test.short_description = 'Users per Test'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)

    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.creator != request.user:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.creator != request.user:
            return False
        return True


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

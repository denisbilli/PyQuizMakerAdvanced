# myapp/admin.py

from django.contrib import admin
from .models import *

from django.contrib.auth.models import User
from django.http import FileResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import User


class ExerciseInline(admin.StackedInline):  # This allows you to add/edit Exercises directly from the Test admin page.
    model = Exercise
    extra = 1  # Number of extra empty forms


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3


class ExerciseAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('title', 'test', 'type')
    list_filter = ['test', 'type']
    search_fields = ['title']


class TestAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_graded', 'due_date')
    list_filter = ['is_graded']
    search_fields = ['name']
    inlines = [ExerciseInline]  # Add the inline to the admin


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'answer_text', 'answer_choice')
    list_filter = ['user', 'exercise']
    search_fields = ['user__username', 'exercise__title']


class UsersPerTestView(PermissionRequiredMixin, DetailView):
    model = Test
    template_name = "admin/your_app_name/users_per_test.html"  # replace "your_app_name" with your app name
    permission_required = "your_app_name.view_test"  # replace "your_app_name" with your app name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.filter(submission__exercise__test=self.object).distinct()
        return context


admin.site.register(Test, TestAdmin)
admin.site.register(Exercise, ExerciseAdmin)
admin.site.register(Submission, SubmissionAdmin)
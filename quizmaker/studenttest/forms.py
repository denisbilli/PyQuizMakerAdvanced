# forms.py

from django import forms
from .models import *
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import User
from django import forms


class AssignTestsToCourseForm(forms.Form):
    course = forms.ModelChoiceField(queryset=Course.objects.all())


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file', 'answer_text', 'answer_choice']

    def save(self, commit=True):
        submission = super().save(commit=False)
        submission.user = self.user
        submission.exercise = self.exercise

        answer_text = self.cleaned_data.get('answer_text')
        answer_choice = self.cleaned_data.get('answer_choice')

        print("User: " + str(submission.user))
        print("Exercise: " + str(submission.exercise))
        print("Text Answer: " + str(answer_text))
        print("Choice Answer: " + str(answer_choice))

        if commit:
            submission.save()

        return submission


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    username = forms.CharField(max_length=30)  # Aggiungi questo campo

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'password1', 'password2', )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.username = self.cleaned_data['username']

        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput)


class UpdateProfileForm(UserChangeForm):
    password = None  # this line will exclude the password field
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)

    class Meta:
        model = User
        fields = ('first_name', 'last_name')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user

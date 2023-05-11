# views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import SubmissionForm, RegistrationForm, LoginForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import admin

from django.http import FileResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO


@login_required
def test_list(request):
    tests = Test.objects.filter(enabled=True)
    return render(request, 'test_list.html', {'tests': tests})


@login_required
def exercise_list(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    exercises = Exercise.objects.filter(test=test)
    completed_exercises = Submission.objects.filter(user=request.user, exercise__in=exercises).values_list('exercise', flat=True)

    return render(request, 'exercise_list.html', {
        'test': test,
        'exercises': exercises,
        'completed_exercises': completed_exercises
    })


@login_required
def submit_test(request, test_id):
    test = Test.objects.get(id=test_id)
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = request.user
            submission.test = test
            submission.save()
            return redirect('test_list')
    else:
        form = SubmissionForm()
    return render(request, 'submit_test.html', {'test': test, 'form': form})


@login_required
def submit_exercise(request, exercise_id):  # Change parameter to exercise_id
    exercise = get_object_or_404(Exercise, id=exercise_id)
    test = exercise.test  # Get the related test

    try:
        submission = Submission.objects.get(user=request.user, exercise=exercise)
        print("Submission already exists!")
    except Submission.DoesNotExist:
        submission = None

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            if test.is_graded and test.due_date < timezone.now():
                return render(request, 'error.html', {'message': 'The due date for this test has passed.'})
            form.user = request.user
            form.exercise = exercise
            form.save(commit=True)
            return redirect('exercise_list', test_id=exercise.test.id)
    else:
        form = SubmissionForm(instance=submission)

    return render(request, 'submit_exercise.html', {'exercise': exercise, 'form': form, 'submission': submission})


@login_required
def user_exercises(request, user_id):
    user = get_object_or_404(User, id=user_id)
    submissions = user.submission_set.all().order_by('exercise__title')
    return render(request, 'user_exercises.html', {'submissions': submissions, 'user': user})


@login_required
def user_exercises_pdf(request, user_id):
    user = get_object_or_404(User, id=user_id)
    submissions = user.submission_set.all().order_by('exercise__title')

    template_path = 'user_exercises.html'
    context = {'submissions': submissions, 'user': user}
    template = get_template(template_path)
    html = template.render(context)

    result = BytesIO()

    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return FileResponse(result, content_type='application/pdf')

    return None


def register(request):
    register_form = RegistrationForm()
    login_form = LoginForm()

    if request.method == 'POST':
        if 'register' in request.POST:  # This will be true if the user is trying to register
            register_form = RegistrationForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                return redirect('test_list')
        elif 'login' in request.POST:  # This will be true if the user is trying to log in
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                user = authenticate(request, username=login_form.cleaned_data.get('username'), password=login_form.cleaned_data.get('password'))
                if user is not None:
                    login(request, user)
                    return redirect('test_list')

    return render(request, 'register.html', {'register_form': register_form, 'login_form': login_form})

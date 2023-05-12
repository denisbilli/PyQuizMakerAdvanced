# views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import SubmissionForm, RegistrationForm, LoginForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import admin

from django.http import FileResponse
from django.views import View
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
from django.utils.text import slugify
from datetime import datetime
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Preformatted
import copy
from django.utils import timezone


@login_required
def test_list(request):
    now = timezone.now()
    tests = Test.objects.filter(enabled=True, is_graded=False)
    tests = tests | Test.objects.filter(enabled=True, is_graded=True, due_date__gte=now)
    return render(request, 'test_list.html', {'tests': tests})


@login_required
def exercise_list(request, test_id):
    now = timezone.now()
    test = get_object_or_404(Test, id=test_id)
    if test.is_graded and test.due_date < now:
        return redirect('test_list')
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
def submit_exercise(request, exercise_id):
    now = timezone.now()
    exercise = get_object_or_404(Exercise, id=exercise_id)
    test = exercise.test  # Get the related test

    try:
        submission = Submission.objects.get(user=request.user, exercise=exercise)
        print("Submission already exists!")
    except Submission.DoesNotExist:
        submission = None

    if request.method == 'POST':
        if not test.is_graded:
            exercise.signed = not exercise.signed
            exercise.save()
            return redirect('exercise_list', test_id=exercise.test.id)
        else:
            form = SubmissionForm(request.POST, request.FILES, instance=submission)
            if form.is_valid():
                if test.is_graded and test.due_date < timezone.now():
                    return render(request, 'error.html', {'message': 'The due date for this test has passed.'})
                form.user = request.user
                form.exercise = exercise
                form.save(commit=True)
                return redirect('exercise_list', test_id=exercise.test.id)
    else:
        if test.is_graded and test.due_date < now:
            return redirect('test_list')
        form = SubmissionForm(instance=submission)

    return render(request, 'submit_exercise.html', {'exercise': exercise, 'form': form, 'submission': submission})


@login_required
def duplicate_exercise(request, exercise_id):
    exercise = get_object_or_404(Exercise, pk=exercise_id)
    new_exercise = copy.deepcopy(exercise)
    new_exercise.pk = None
    new_exercise.save()
    return redirect(request.META.get('HTTP_REFERER'))


@login_required
def user_exercises(request, user_id):
    user = get_object_or_404(User, id=user_id)
    submissions = user.submission_set.all().order_by('exercise__title')
    return render(request, 'user_exercises.html', {'submissions': submissions, 'user': user})


@login_required
def user_exercises_pdf(request, user_id, test_id):
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


class UserTestReportView(View):
    def get(self, request, *args, **kwargs):
        test = get_object_or_404(Test, pk=kwargs['test_pk'])
        user = get_object_or_404(User, pk=kwargs['user_pk'])
        submissions = user.submission_set.filter(exercise__test=test)

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        title = f"{user.username}'s Submissions for {test.name}"
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 24))

        monospace_style = ParagraphStyle('monospace', parent=styles['BodyText'], fontName='Courier', fontSize=8)

        for submission in submissions:
            exercise_title = Paragraph(f"Exercise: {submission.exercise.title}", styles['Heading2'])
            elements.append(exercise_title)

            if submission.exercise.type in ['O']:
                answer_text = Paragraph(f"Answer: {submission.answer_text}", styles['BodyText'])
                elements.append(answer_text)
            elif submission.exercise.type == 'M':
                answer_choice = Paragraph(f"Answer: {submission.answer_choice.text}", styles['BodyText'])
                elements.append(answer_choice)
            elif submission.exercise.type == 'C':
                elements.append(Paragraph("Answer:", styles['BodyText']))
                code = Preformatted(submission.answer_text.replace('\r',''), monospace_style)
                elements.append(code)

            elements.append(Spacer(1, 12))

        doc.build(elements)

        buffer.seek(0)

        username_slug = slugify(user.username)
        testname_slug = slugify(test.name)
        date_str = test.due_date.strftime("%Y%m%d")  # Current date in YYYYMMDD format

        # Creating the filename
        filename = f"{username_slug}_{date_str}_{testname_slug}.pdf"

        # Pass the filename when returning the response
        response = FileResponse(buffer, as_attachment=True, filename=filename)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


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

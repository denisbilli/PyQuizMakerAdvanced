# views.py
import io
import copy

from django.http import FileResponse
from django.views import View
from django.utils import timezone
from django.utils.text import slugify
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib import messages
from django.db.models import Sum
from django.core.files.storage import default_storage
from django.db.models import Count, Q

# ReportLab
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Preformatted, SimpleDocTemplate
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT

from .models import *
from .forms import SubmissionForm, RegistrationForm, LoginForm, UpdateProfileForm, PasswordChangeForm


class MyDocTemplate(BaseDocTemplate):
    def __init__(self, filename, user, test, **kwargs):
        self.user = user
        self.test = test
        BaseDocTemplate.__init__(self, filename, **kwargs)
        template = PageTemplate('normal', [Frame(20*mm, 20*mm, (A4[0]-40*mm), (A4[1]-40*mm), id='main')])
        template.beforeDrawPage = self.before_page
        self.addPageTemplates([template])

    def before_page(self, canvas, document):
        canvas.saveState()
        styles = getSampleStyleSheet()

        # Header
        header = Paragraph(f"Date: {self.test.due_date.strftime('%d/%m/%Y')}", styles['Normal'])
        w, h = header.wrap(document.width, document.topMargin)
        print(f"Header width: {w}, Header height: {h}")  # Debugging line
        print(f"Document leftMargin: {document.leftMargin}, Document height: {document.pagesize[1]}")  # Debugging line
        header.drawOn(canvas, document.leftMargin, document.pagesize[1] - h - 10 * mm)

        right_aligned_style = ParagraphStyle('RightAligned', parent=styles['Normal'], alignment=TA_RIGHT)
        header2 = Paragraph(f"{self.user.first_name} {self.user.last_name}", right_aligned_style)
        w, h = header2.wrap(200, document.topMargin)
        print(f"Header2 width: {w}, Header2 height: {h}")  # Debugging line
        print(f"Document width: {document.pagesize[0]}, Document rightMargin: {document.rightMargin}")  # Debugging line
        header2.drawOn(canvas, document.pagesize[0] - w - 20 * mm, document.pagesize[1] - h - 10 * mm)

        # Footer
        footer = Paragraph(f"Page: {document.page}", styles['Normal'])
        w, h = footer.wrap(document.width, document.bottomMargin)
        print(f"Footer width: {w}, Footer height: {h}")  # Debugging line
        print(
            f"Document width: {document.pagesize[0]}, Document bottomMargin: {document.bottomMargin}")  # Debugging line
        footer.drawOn(canvas, document.pagesize[0] - w - 20 * mm, h)

        canvas.restoreState()


@login_required
def profile(request):
    form = UpdateProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'update_profile':
            form = UpdateProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your profile was successfully updated!')
                return redirect('profile')

        elif form_type == 'change_password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Update session to avoid logging out
                messages.success(request, 'Your password was successfully updated!')
                return redirect('profile')

        else:
            messages.error(request, 'Something went wrong.')

    return render(request, 'profile.html', {'form': form, 'password_form': password_form})


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
    total_score = test.exercises.aggregate(total=Sum('score'))['total'] or 0

    cannot_enter_view = not request.user.is_superuser and (
                (test.is_graded and test.due_date < now) or (not test.enabled))

    if cannot_enter_view:
        return redirect('test_list')

    exercises = Exercise.objects.filter(test=test, enabled=True).annotate(
        signed_count=Count('userexercise', filter=Q(userexercise__signed=True))
    )
    completed_exercises = Submission.objects.filter(user=request.user, exercise__in=exercises).values_list('exercise', flat=True)

    # Fetch the UserExercise objects related to the current user and test
    user_exercises = UserExercise.objects.filter(user=request.user, exercise__test=test)

    # Extract the ids of the signed exercises into a list
    signed_exercises = [ue.exercise.id for ue in user_exercises if ue.signed]

    return render(request, 'exercise_list.html', {
        'test': test,
        'exercises': exercises,
        'completed_exercises': completed_exercises,
        'signed_exercises': signed_exercises,
        'total_score': total_score
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

    user_exercise, created = UserExercise.objects.get_or_create(user=request.user, exercise=exercise)

    if request.method == 'POST':
        if not test.is_graded:
            user_exercise.signed = not user_exercise.signed
            user_exercise.save()
            return redirect('exercise_list', test_id=exercise.test.id)
        else:
            form = SubmissionForm(request.POST, request.FILES, instance=submission)
            if form.is_valid():
                print("Form valido!")
                if test.is_graded and test.due_date < now:
                    print("Errore nella data!" + str(test.due_date) + " " + str(now))
                    return render(request, 'error.html', {'message': 'The due date for this test has passed.'})
                form.user = request.user
                form.exercise = exercise
                form.save(commit=True)
                return redirect('exercise_list', test_id=exercise.test.id)
    else:
        cannot_enter_view = not request.user.is_superuser and (
                (test.is_graded and test.due_date < now) or (not test.enabled))
        if cannot_enter_view:
            return redirect('test_list')
        form = SubmissionForm(instance=submission)

    return render(request, 'submit_exercise.html', {'exercise': exercise, 'form': form, 'submission': submission,
                                                    'user_exercise': user_exercise})


@login_required
def duplicate_exercise(request, exercise_id):
    exercise = get_object_or_404(Exercise, pk=exercise_id)
    new_exercise = copy.deepcopy(exercise)
    new_exercise.pk = None
    new_exercise.enabled = False
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

        # doc = SimpleDocTemplate(buffer, pagesize=letter)
        doc = MyDocTemplate(buffer, user, test, pagesize=A4)
        # Story = [Spacer(1, 2 * inch), Paragraph("Hello, world!", getSampleStyleSheet()['Normal']), PageBreak()]
        # doc.build(Story)

        styles = getSampleStyleSheet()
        elements = []

        # format the date in a human-readable format
        test_name = Paragraph(f"{test.name}", styles['Title'])
        elements.append(test_name)

        test_details = Paragraph(f"del {test.due_date.strftime('%d/%m/%Y')} di {user.first_name} {user.last_name}",
                                 styles['Title'])
        elements.append(test_details)
        elements.append(Spacer(1, 24))

        monospace_style = ParagraphStyle('monospace', parent=styles['BodyText'], fontName='Courier', fontSize=8)

        for submission in submissions:
            exercise_title = Paragraph(f"Esercizio: {submission.exercise.title}", styles['Heading2'])
            elements.append(exercise_title)

            exercise_text = Paragraph(f"Testo: {submission.exercise.description}", styles['BodyText'])
            elements.append(exercise_text)

            if submission.exercise.type in ['O']:
                answer_text = Paragraph(f"Risposta: {submission.answer_text}", styles['BodyText'])
                elements.append(answer_text)
            elif submission.exercise.type == 'M':
                answer_choice = Paragraph(f"Risposta: {submission.answer_choice.text}", styles['BodyText'])
                elements.append(answer_choice)
            elif submission.exercise.type == 'C':
                elements.append(Paragraph("Risposta:", styles['BodyText']))
                if submission.answer_text:
                    code = Preformatted(submission.answer_text.replace('\r',''), monospace_style)
                elif submission.file:
                    with default_storage.open(submission.file.name, 'r') as f:
                        code_content = f.read()
                    code = Preformatted(code_content.replace('\r',''), monospace_style)
                else:
                    code = Paragraph("No response provided", styles['BodyText'])
                elements.append(code)

            elements.append(Spacer(1, 12))

        doc.build(elements)

        buffer.seek(0)

        username_slug = slugify(user.username)
        testname_slug = slugify(test.name)
        date_slug = test.due_date.strftime("%Y%m%d")  # Date in YYYYMMDD format for the filename

        # Creating the filename
        filename = f"{username_slug}_{date_slug}_{testname_slug}.pdf"

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

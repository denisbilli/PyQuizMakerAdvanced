# views.py
import io
import copy
import chardet
import codecs
import html

from django.http import FileResponse
from django.views import View
from django.utils import timezone
from django.utils.text import slugify
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib import messages
from django.db.models import Sum, Avg
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
def course_list(request):
    # visible to everyone (visible_to is empty) or visible to the current user.
    courses = Course.objects.filter(
        Q(visible_to__isnull=True) | Q(visible_to=request.user),
        enabled=True,
    )
    return render(request, 'course_list.html', {'courses': courses, 'user': request.user})


@login_required
def enroll_in_course(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    # Controlla se l'utente ha già effettuato l'iscrizione
    if not course.is_student_enrolled(request.user):
        Enrollment.objects.create(student=request.user, course=course)

    # Reindirizza l'utente alla lista dei test per il corso
    return redirect('test_list_by_course', course_id=course_id)


@login_required
def test_list(request):
    # Show only the tests that are either
    # visible to everyone (visible_to is empty) or visible to the current user.
    tests = Test.objects.filter(
        Q(visible_to__isnull=True) | Q(visible_to=request.user),
        enabled=True,
    )
    return render(request, 'test_list.html', {'tests': tests})


@login_required
def test_list_by_course(request, course_id):
    # Recupera il corso specificato o restituisce una pagina 404 se non trovato
    course = get_object_or_404(Course, pk=course_id)

    cannot_enter_view = not request.user.is_superuser and (
                (course.enabled and not course.is_student_enrolled(request.user)) or (not course.enabled))

    print(f"{request.user} can view the course {course_id}? {not cannot_enter_view} because: \n"
          f"- is {request.user} superuser? {request.user.is_superuser}\n"
          f"- is course {course.name} enabled? {course.enabled}\n"
          f"- is student {request.user} enrolled in course {course.name}? {course.is_student_enrolled(request.user)}\n")

    if cannot_enter_view:
        back_url = request.META.get('HTTP_REFERER',
                                    '/')  # Ottieni l'URL del chiamante, default alla home se non presente
        return render(request, 'error.html', {
            'message': f'Spiacente! Non hai i permessi per accedere al corso {course.name}',
            'back_url': back_url
        })

    # Filtra i test associati a quel corso specifico
    tests = Test.objects.filter(course=course)

    # Puoi aggiungere ulteriore logica qui, ad esempio controllare permessi specifici

    # Restituisce i test al template
    return render(request, 'test_list.html', {'course': course, 'tests': tests, 'has_footer': True })


@login_required
def exercise_list(request, test_id):
    now = timezone.now()
    test = get_object_or_404(Test, id=test_id)
    total_score = test.exercises.aggregate(total=Sum('score'))['total'] or 0

    cannot_enter_view = not request.user.is_superuser and (
                (test.is_graded and test.due_date < now) or (not test.enabled))

    if cannot_enter_view:
        print(f"L'utente {request.user.username} non ha i permessi per accedere al test {test.name}")
        print("Check test finale: " + str(test.is_graded))
        print("Check test abilitato: " + str(test.enabled))
        if test.due_date is not None:
            print("Check data: " + str(test.due_date.strftime("%d/%m/%Y %H:%M")) + " " +
                  str(now.strftime("%d/%m/%Y %H:%M")))
        else:
            print("Check data: Nessuna data impostata")
        return render(request, 'error.html', {'message': f'Spiacente! Non hai i permessi per '
                                                         f'accedere al test {test.name}'})

    exercises = Exercise.objects.filter(test=test, enabled=True).annotate(
        signed_count=Count('userexercise', filter=Q(userexercise__signed=True)),
        average_rating=Avg('userexercise__stars')  # Compute the average rating here
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
        'total_score': total_score,
        'has_footer': True,
        'fixed_footer': True
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
            rating = request.POST.get('rating')
            signed = request.POST.get('signed')
            print(f'The exercise has been rated {rating} and is {signed}')
            if rating is not None:
                user_exercise.stars = rating
            if signed is not None:
                user_exercise.signed = True
            else:
                user_exercise.signed = False
            user_exercise.save()
            return redirect('exercise_list', test_id=exercise.test.id)
        else:
            form = SubmissionForm(request.POST, request.FILES, instance=submission)
            if form.is_valid():
                print("Form valido!")
                if test.is_graded and test.due_date < now:
                    print("L'utente " + request.user.username + " non ha i permessi per accedere al test " + test.name)
                    print("Check test finale: " + str(test.is_graded))
                    print("Check test abilitato: " + str(test.enabled))
                    if test.due_date is not None:
                        print("Check data: " + str(test.due_date.strftime("%d/%m/%Y %H:%M")) + " " +
                              str(now.strftime("%d/%m/%Y %H:%M")))
                    else:
                        print("Check data: Nessuna data impostata")
                    return render(request, 'error.html', {'message': 'La data di consegna è passata, oppure il test '
                                                                     'non è abilitato.'})
                form.user = request.user
                form.exercise = exercise
                form.save(commit=True)
                return redirect('exercise_list', test_id=exercise.test.id)
    else:
        cannot_enter_view = not request.user.is_superuser and (
                (test.is_graded and test.due_date < now) or (not test.enabled))
        if cannot_enter_view:
            print("L'utente " + request.user.username + " non ha i permessi per accedere al test " + test.name)
            print("Check test finale: " + str(test.is_graded))
            print("Check test abilitato: " + str(test.enabled))
            if test.due_date is not None:
                print("Check data: " + str(test.due_date.strftime("%d/%m/%Y %H:%M")) + " " +
                      str(now.strftime("%d/%m/%Y %H:%M")))
            else:
                print("Check data: Nessuna data impostata")
            return render(request, 'error.html', {'message': 'La data di consegna è passata, oppure il test non è '
                                                             'abilitato.'})
        form = SubmissionForm(instance=submission)

    return render(request, 'submit_exercise.html', {'exercise': exercise,
                                                    'form': form,
                                                    'submission': submission,
                                                    'user_exercise': user_exercise,
                                                    'has_footer': True,
                                                    'fixed_footer': True })


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

        heading_style = ParagraphStyle('monospace', parent=styles['Heading2'], fontName='Helvetica', fontSize=12)
        body_style = ParagraphStyle('monospace', parent=styles['Heading2'], fontName='Helvetica', fontSize=10)
        monospace_style = ParagraphStyle('monospace', parent=styles['BodyText'], fontName='Courier', fontSize=10)

        for submission in submissions:
            exercise_title = Paragraph(f"Esercizio {submission.exercise.title} - Punti {submission.exercise.score}", heading_style)
            elements.append(exercise_title)

            exercise_text = Paragraph(f"Testo: {submission.exercise.description}", body_style)
            elements.append(exercise_text)
            elements.append(Spacer(1, 12))

            if submission.exercise.type in ['O', 'D']:
                escaped_text = html.escape(submission.answer_text)
                answer_text = Paragraph(f"Risposta: {escaped_text}", monospace_style)
                elements.append(answer_text)
            elif submission.exercise.type == 'M':
                answer_choice = Paragraph(f"Risposta: {submission.answer_choice.text}", monospace_style)
                elements.append(answer_choice)
            elif submission.exercise.type == 'C':
                elements.append(Paragraph("Risposta:", monospace_style))
                if submission.answer_text:
                    code = Preformatted(submission.answer_text.replace('\r\n', '\n').replace('\t', ' '), monospace_style)
                elif submission.file:
                    print("trying to open file" + submission.file.name)
                    with default_storage.open(submission.file.name, 'rb') as f:
                        rawdata = f.read()
                    result = chardet.detect(rawdata)
                    charenc = result['encoding']
                    with codecs.open(default_storage.path(submission.file.name), 'r', encoding=charenc) as f:
                        code_content = f.read()
                    code = Preformatted(code_content.replace('\r\n', '\n').replace('\t', ' '), monospace_style)
                else:
                    code = Paragraph("No response provided", monospace_style)
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
                return redirect('course_list')
        elif 'login' in request.POST:  # This will be true if the user is trying to log in
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                user = authenticate(request, username=login_form.cleaned_data.get('username'), password=login_form.cleaned_data.get('password'))
                if user is not None:
                    login(request, user)
                    return redirect('course_list')

    return render(request, 'register.html', {'register_form': register_form, 'login_form': login_form})

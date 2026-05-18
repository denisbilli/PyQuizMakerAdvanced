# PyQuizMakerAdvanced

PyQuizMakerAdvanced is a Django-based platform for course testing workflows, including enrollments, exercises, submissions, and basic reporting.

## Features

- Course and test management
- Student enrollment per course
- Multiple exercise types (open question, multiple choice, code, flowchart)
- Submission handling (text and file upload)
- User profile and password management
- Basic report generation
- Internationalization support

## Tech Stack

- Python
- Django 4.2
- django-modeltranslation
- ReportLab

## Project Structure

```text
PyQuizMakerAdvanced/
└── quizmaker/
    ├── manage.py
    ├── requirements.txt
    ├── quizmaker/      # Django project settings and root urls
    └── studenttest/    # Main app (courses, tests, exercises, submissions)
```

## Quick Start

From repository root:

```bash
cd quizmaker
python -m venv .venv
```

Activate virtual environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Install dependencies and run migrations:

```bash
pip install -r requirements.txt
python manage.py migrate
```

Create an admin user and run the server:

```bash
python manage.py createsuperuser
python manage.py runserver
```

Then open http://127.0.0.1:8000/.

## Notes

- The main user-facing routes are exposed by the `studenttest` app.
- Admin is available under `/admin/` (localized by Django i18n patterns).

## License

See repository license files and commit history for usage terms.

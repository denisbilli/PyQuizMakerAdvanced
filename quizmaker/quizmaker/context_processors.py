from django.conf import settings

def languages_processor(request):
    return {'languages': settings.LANGUAGES}
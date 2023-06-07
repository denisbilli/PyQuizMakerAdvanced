from modeltranslation.translator import register, TranslationOptions
from .models import Exercise, Test


@register(Test)
class TestTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


@register(Exercise)
class ExerciseTranslationOptions(TranslationOptions):
    fields = ('title', 'description', 'expected_answer')

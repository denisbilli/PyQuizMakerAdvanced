# myapp/templatetags/course_filters.py
from django import template
from ..models import Enrollment

register = template.Library()

@register.filter(name='is_student_enrolled')
def is_student_enrolled(course, user):
    return Enrollment.objects.filter(student=user, course=course).exists()

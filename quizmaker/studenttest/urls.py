# myapp/urls.py

from django.contrib.auth.views import LogoutView
from django.urls import path
from django.urls import include, path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('courses/<int:course_id>/tests/', views.test_list_by_course, name='test_list_by_course'),
    path('courses/enroll/<int:course_id>/', views.enroll_in_course, name='enroll_in_course'),
    path('i18n/', include('django.conf.urls.i18n')),
    path('tests/<int:test_id>/exercises/', views.exercise_list, name='exercise_list'),
    path('register/', views.register, name='register'),
    path('logout/', LogoutView.as_view(next_page='course_list'), name='logout'),
    path('exercises/<int:exercise_id>/submit/', views.submit_exercise, name='submit_exercise'),
    path('exercise/<int:exercise_id>/duplicate/', views.duplicate_exercise, name='duplicate_exercise'),
    path('test/<int:test_pk>/user/<int:user_pk>/report/', views.UserTestReportView.as_view(), name='user_test_report'),
    path('profile/', views.profile, name='profile'),
]

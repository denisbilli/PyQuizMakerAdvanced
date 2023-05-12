# myapp/urls.py

from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views

urlpatterns = [
    path('', views.test_list, name='test_list'),
    path('tests/<int:test_id>/exercises/', views.exercise_list, name='exercise_list'),
    path('register/', views.register, name='register'),
    path('logout/', LogoutView.as_view(next_page='test_list'), name='logout'),
    path('exercises/<int:exercise_id>/submit/', views.submit_exercise, name='submit_exercise'),
    path('exercise/<int:exercise_id>/duplicate/', views.duplicate_exercise, name='duplicate_exercise'),
    path('test/<int:test_pk>/user/<int:user_pk>/report/', views.UserTestReportView.as_view(), name='user_test_report'),
]

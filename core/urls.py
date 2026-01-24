from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    LoginView,
    home,
    teacher_dashboard,
    teacher_award,
    teacher_ranking,
    student_dashboard,
    student_shop,
    student_redeem,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", home, name="home"),
    path("teacher/", teacher_dashboard, name="teacher_dashboard"),
    path("teacher/award/<int:student_id>/", teacher_award, name="teacher_award"),
    path("teacher/ranking/", teacher_ranking, name="teacher_ranking"),
    path("student/", student_dashboard, name="student_dashboard"),
    path("student/shop/", student_shop, name="student_shop"),
    path("student/redeem/<int:bonus_id>/", student_redeem, name="student_redeem"),
]

from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    LoginView,
    home,
    teacher_dashboard,
    teacher_award,
    teacher_ranking,
    teacher_guidelines,
    teacher_confirm_bonus_request,
    student_dashboard,
    student_shop,
    student_redeem,
    student_reserve_points,
    student_withdraw_reservation,
    student_confirm_group_purchase,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", home, name="home"),
    path("teacher/", teacher_dashboard, name="teacher_dashboard"),
    path("teacher/award/<int:student_id>/", teacher_award, name="teacher_award"),
    path("teacher/ranking/", teacher_ranking, name="teacher_ranking"),
    path("teacher/guidelines/", teacher_guidelines, name="teacher_guidelines"),
    path(
        "teacher/bonus-request/<int:request_id>/confirm/",
        teacher_confirm_bonus_request,
        name="teacher_confirm_bonus_request",
    ),
    path("student/", student_dashboard, name="student_dashboard"),
    path("student/shop/", student_shop, name="student_shop"),
    path("student/redeem/<int:bonus_id>/", student_redeem, name="student_redeem"),
    path("student/reserve/<int:bonus_id>/", student_reserve_points, name="student_reserve_points"),
    path(
        "student/reserve/<int:bonus_id>/withdraw/",
        student_withdraw_reservation,
        name="student_withdraw_reservation",
    ),
    path(
        "student/reserve/<int:bonus_id>/confirm/",
        student_confirm_group_purchase,
        name="student_confirm_group_purchase",
    ),
]

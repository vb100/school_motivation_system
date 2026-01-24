from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import require_role
from .forms import AwardForm
from .models import BonusItem, PointTransaction, StudentProfile, User
from .services import (
    DomainError,
    award_points,
    get_active_semester,
    redeem_bonus,
    student_balance_points,
    bonus_used_count,
    top_students,
)


class LoginView(auth_views.LoginView):
    template_name = "core/login.html"


def home(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.role and not request.user.is_superuser:
        logout(request)
        messages.error(request, "Vartotojui nepriskirta rolė. Susisiekite su administratoriumi.")
        return redirect("login")
    if request.user.is_superuser or request.user.role == User.Role.ADMIN:
        return redirect("admin:index")
    if request.user.role == User.Role.TEACHER:
        return redirect("teacher_dashboard")
    return redirect("student_dashboard")


@require_role([User.Role.TEACHER])
def teacher_dashboard(request: HttpRequest) -> HttpResponse:
    try:
        semester = get_active_semester()
    except DomainError as exc:
        messages.error(request, exc.message)
        return render(
            request,
            "core/teacher_dashboard.html",
            {
                "semester": None,
                "budget": None,
                "students": StudentProfile.objects.none(),
                "recent_activity": [],
                "top_five": [],
                "query": "",
            },
        )
    teacher_profile = request.user.teacher_profile
    budget = teacher_profile.teacherbudget_set.filter(semester=semester).first()
    students = StudentProfile.objects.all().order_by("display_name")
    query = request.GET.get("q")
    if query:
        students = students.filter(display_name__icontains=query)
    recent_activity = (
        PointTransaction.objects.filter(semester=semester)
        .select_related("student_profile", "created_by__teacher_profile")
        .order_by("-created_at")[:10]
    )
    top_five = top_students(semester)

    context = {
        "semester": semester,
        "budget": budget,
        "students": students,
        "recent_activity": recent_activity,
        "top_five": top_five,
        "query": query or "",
    }
    return render(request, "core/teacher_dashboard.html", context)


@require_role([User.Role.TEACHER])
def teacher_award(request: HttpRequest, student_id: int) -> HttpResponse:
    student = get_object_or_404(StudentProfile, pk=student_id)
    if request.method == "POST":
        form = AwardForm(request.POST)
        if form.is_valid():
            try:
                award_points(
                    teacher_user=request.user,
                    student=student,
                    points=form.cleaned_data["points"],
                    message=form.cleaned_data["message"],
                )
                messages.success(request, "Taškai sėkmingai skirti!")
                return redirect("teacher_dashboard")
            except DomainError as exc:
                messages.error(request, exc.message)
    else:
        form = AwardForm()

    return render(request, "core/teacher_award.html", {"student": student, "form": form})


@require_role([User.Role.TEACHER])
def teacher_ranking(request: HttpRequest) -> HttpResponse:
    try:
        semester = get_active_semester()
        top_five = top_students(semester)
    except DomainError as exc:
        messages.error(request, exc.message)
        semester = None
        top_five = []
    return render(request, "core/teacher_ranking.html", {"top_five": top_five, "semester": semester})


@require_role([User.Role.STUDENT])
def student_dashboard(request: HttpRequest) -> HttpResponse:
    try:
        semester = get_active_semester()
    except DomainError as exc:
        messages.error(request, exc.message)
        return render(
            request,
            "core/student_dashboard.html",
            {
                "semester": None,
                "balance": 0,
                "recent_activity": [],
                "school_activity": [],
            },
        )
    student_profile = request.user.student_profile
    balance = student_balance_points(student_profile, semester)
    recent_activity = (
        PointTransaction.objects.filter(semester=semester, student_profile=student_profile)
        .select_related("created_by__teacher_profile")
        .order_by("-created_at")[:10]
    )
    school_activity = (
        PointTransaction.objects.filter(semester=semester)
        .select_related("created_by__teacher_profile", "student_profile")
        .order_by("-created_at")[:10]
    )

    context = {
        "semester": semester,
        "balance": balance,
        "recent_activity": recent_activity,
        "school_activity": school_activity,
    }
    return render(request, "core/student_dashboard.html", context)


@require_role([User.Role.STUDENT])
def student_shop(request: HttpRequest) -> HttpResponse:
    try:
        semester = get_active_semester()
    except DomainError as exc:
        messages.error(request, exc.message)
        return render(request, "core/student_shop.html", {"balance": 0, "bonuses_info": []})
    student_profile = request.user.student_profile
    balance = student_balance_points(student_profile, semester)
    bonuses = BonusItem.objects.filter(is_active=True).order_by("price_points")
    bonuses_info = []
    for bonus in bonuses:
        used = bonus_used_count(student_profile, semester, bonus)
        remaining_uses = max(bonus.max_uses_per_student - used, 0)
        bonuses_info.append(
            {
                "bonus": bonus,
                "used": used,
                "remaining_uses": remaining_uses,
                "can_redeem": remaining_uses > 0 and balance >= bonus.price_points,
            }
        )

    context = {
        "balance": balance,
        "bonuses_info": bonuses_info,
    }
    return render(request, "core/student_shop.html", context)


@require_role([User.Role.STUDENT])
def student_redeem(request: HttpRequest, bonus_id: int) -> HttpResponse:
    bonus = get_object_or_404(BonusItem, pk=bonus_id)
    if request.method == "POST":
        try:
            redeem_bonus(request.user, bonus)
            messages.success(request, "Bonusas sėkmingai išpirktas!")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("student_shop")

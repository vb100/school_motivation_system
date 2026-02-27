from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import require_role
from .forms import AwardForm
from .models import (
    BonusItem,
    BonusRedemptionRequest,
    GroupPurchase,
    GroupContribution,
    PointTransaction,
    StudentProfile,
    TeacherBudget,
    User,
)
from .services import (
    DomainError,
    award_points,
    get_active_semester,
    get_school_name,
    get_school_settings,
    confirm_group_purchase,
    reserve_group_points,
    withdraw_group_reservation,
    redeem_bonus,
    create_bonus_redemption_request,
    confirm_bonus_redemption_request,
    student_balance_points,
    bonus_used_count,
    student_reserved_points,
    top_students,
)


class LoginView(auth_views.LoginView):
    template_name = "core/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_settings = get_school_settings()
        context["school_logo_url"] = school_settings.logo.url if school_settings and school_settings.logo else ""
        context["login_background_url"] = (
            school_settings.login_background.url
            if school_settings and school_settings.login_background
            else ""
        )
        return context


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
    school_settings = get_school_settings()
    school_logo_url = school_settings.logo.url if school_settings and school_settings.logo else ""
    query = (request.GET.get("q") or "").strip()
    selected_class = (request.GET.get("class_name") or "").strip()
    class_options = list(
        StudentProfile.objects.exclude(class_name="")
        .order_by("class_name")
        .values_list("class_name", flat=True)
        .distinct()
    )
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
                "pending_bonus_requests": [],
                "top_five": [],
                "query": query,
                "selected_class": selected_class,
                "class_options": class_options,
                "school_name": get_school_name(),
                "school_logo_url": school_logo_url,
                "bonuses_payload": [],
            },
        )
    teacher_profile = request.user.teacher_profile
    budget = teacher_profile.teacherbudget_set.filter(semester=semester).first()
    students = StudentProfile.objects.all().order_by("display_name")
    if query:
        students = students.filter(display_name__icontains=query)
    if selected_class:
        students = students.filter(class_name__iexact=selected_class)
    recent_activity = (
        PointTransaction.objects.filter(semester=semester)
        .select_related("student_profile", "created_by__teacher_profile")
        .order_by("-created_at")[:10]
    )
    pending_bonus_requests = (
        BonusRedemptionRequest.objects.filter(
            requested_teacher=teacher_profile,
            status=BonusRedemptionRequest.Status.PENDING,
        )
        .select_related("student_profile", "bonus_item", "semester")
        .order_by("created_at")
    )
    top_five = top_students(semester)
    bonuses = list(BonusItem.objects.filter(is_active=True).order_by("price_points"))
    bonuses_payload = [{"title": bonus.title_lt, "price_points": bonus.price_points} for bonus in bonuses]

    context = {
        "semester": semester,
        "budget": budget,
        "students": students,
        "recent_activity": recent_activity,
        "pending_bonus_requests": pending_bonus_requests,
        "top_five": top_five,
        "query": query,
        "selected_class": selected_class,
        "class_options": class_options,
        "school_name": get_school_name(),
        "school_logo_url": school_logo_url,
        "bonuses_payload": bonuses_payload,
    }
    return render(request, "core/teacher_dashboard.html", context)


@require_role([User.Role.TEACHER])
def teacher_award(request: HttpRequest, student_id: int) -> HttpResponse:
    student = get_object_or_404(StudentProfile, pk=student_id)
    try:
        semester = get_active_semester()
        budget = (
            TeacherBudget.objects.filter(teacher_profile=request.user.teacher_profile, semester=semester).first()
        )
        remaining_budget = budget.remaining_points if budget else None
    except DomainError:
        remaining_budget = None
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

    return render(
        request,
        "core/teacher_award.html",
        {"student": student, "form": form, "remaining_budget": remaining_budget},
    )


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
    school_settings = get_school_settings()
    school_logo_url = school_settings.logo.url if school_settings and school_settings.logo else ""
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
                "school_name": get_school_name(),
                "school_logo_url": school_logo_url,
                "last_purchase": None,
            },
        )
    student_profile = request.user.student_profile
    balance = student_balance_points(student_profile, semester)
    last_purchase = (
        PointTransaction.objects.filter(
            semester=semester,
            student_profile=student_profile,
            tx_type=PointTransaction.TxType.REDEEM,
        )
        .order_by("-created_at")
        .first()
    )
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
        "current_student_id": student_profile.id,
        "school_name": get_school_name(),
        "school_logo_url": school_logo_url,
        "last_purchase": last_purchase,
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
    reserved = student_reserved_points(student_profile, semester)
    available_points = balance - reserved
    bonuses = BonusItem.objects.filter(is_active=True).prefetch_related("assigned_teachers").order_by("price_points")
    pending_requests_by_bonus = {
        bonus_request.bonus_item_id: bonus_request
        for bonus_request in BonusRedemptionRequest.objects.filter(
            semester=semester,
            student_profile=student_profile,
            status=BonusRedemptionRequest.Status.PENDING,
        ).select_related("requested_teacher")
    }
    bonuses_info = []
    for bonus in bonuses:
        used = bonus_used_count(student_profile, semester, bonus)
        remaining_uses = max(bonus.max_uses_per_student - used, 0)
        requires_teacher_confirmation = bonus.category == BonusItem.Category.POINTS_RELATED
        assigned_teachers = list(bonus.assigned_teachers.all().order_by("display_name"))
        pending_request = pending_requests_by_bonus.get(bonus.id)

        if requires_teacher_confirmation:
            group_purchase = None
            total_reserved = 0
            my_amount = 0
            my_confirmed = False
            remaining_to_fund = bonus.price_points
            can_withdraw = False
        else:
            group_purchase = GroupPurchase.objects.filter(
                semester=semester,
                bonus_item=bonus,
                status__in=[GroupPurchase.Status.OPEN, GroupPurchase.Status.AWAITING_CONFIRMATION],
            ).first()
            if group_purchase:
                total_reserved = (
                    GroupContribution.objects.filter(group_purchase=group_purchase)
                    .aggregate(total=Sum("amount"))
                    .get("total")
                    or 0
                )
                my_contribution = (
                    GroupContribution.objects.filter(group_purchase=group_purchase, student_profile=student_profile)
                    .first()
                )
                my_amount = my_contribution.amount if my_contribution else 0
                my_confirmed = bool(my_contribution and my_contribution.confirmed_at)
                remaining_to_fund = max(bonus.price_points - total_reserved, 0)
                can_withdraw = (
                    my_contribution is not None
                    and GroupContribution.objects.filter(group_purchase=group_purchase)
                    .exclude(student_profile=student_profile)
                    .count()
                    == 0
                    and group_purchase.status != GroupPurchase.Status.COMPLETED
                )
            else:
                total_reserved = 0
                my_amount = 0
                my_confirmed = False
                remaining_to_fund = bonus.price_points
                can_withdraw = False

        bonuses_info.append(
            {
                "bonus": bonus,
                "used": used,
                "remaining_uses": remaining_uses,
                "can_redeem": (
                    not requires_teacher_confirmation
                    and remaining_uses > 0
                    and available_points >= bonus.price_points
                ),
                "group_purchase": group_purchase,
                "group_reserved_total": total_reserved,
                "group_remaining": remaining_to_fund,
                "group_my_amount": my_amount,
                "group_my_confirmed": my_confirmed,
                "group_can_withdraw": can_withdraw,
                "requires_teacher_confirmation": requires_teacher_confirmation,
                "assigned_teachers": assigned_teachers,
                "pending_request": pending_request,
                "can_request_confirmation": (
                    requires_teacher_confirmation
                    and remaining_uses > 0
                    and available_points >= bonus.price_points
                    and pending_request is None
                    and len(assigned_teachers) > 0
                ),
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
            if bonus.category == BonusItem.Category.POINTS_RELATED:
                teacher_id_raw = request.POST.get("teacher_id")
                teacher_id = int(teacher_id_raw) if teacher_id_raw else None
                create_bonus_redemption_request(request.user, bonus, teacher_id)
                messages.success(request, "Prašymas išsiųstas mokytojui patvirtinti.")
            else:
                redeem_bonus(request.user, bonus)
                messages.success(request, "Bonusas sėkmingai išpirktas!")
        except (TypeError, ValueError):
            messages.error(request, "Pasirinkite mokytoją bonuso patvirtinimui.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("student_shop")


@require_role([User.Role.TEACHER])
def teacher_confirm_bonus_request(request: HttpRequest, request_id: int) -> HttpResponse:
    bonus_request = get_object_or_404(BonusRedemptionRequest, pk=request_id)
    if request.method == "POST":
        try:
            confirm_bonus_redemption_request(request.user, bonus_request)
            messages.success(request, "Prašymas patvirtintas, bonusas išpirktas.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("teacher_dashboard")


@require_role([User.Role.STUDENT])
def student_reserve_points(request: HttpRequest, bonus_id: int) -> HttpResponse:
    bonus = get_object_or_404(BonusItem, pk=bonus_id)
    if request.method == "POST":
        try:
            amount = int(request.POST.get("reserve_amount", "0"))
            reserve_group_points(request.user, bonus, amount)
            messages.success(request, "Taškai sėkmingai rezervuoti!")
        except (ValueError, TypeError):
            messages.error(request, "Įveskite teisingą taškų kiekį.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("student_shop")


@require_role([User.Role.STUDENT])
def student_withdraw_reservation(request: HttpRequest, bonus_id: int) -> HttpResponse:
    bonus = get_object_or_404(BonusItem, pk=bonus_id)
    if request.method == "POST":
        try:
            withdraw_group_reservation(request.user, bonus)
            messages.success(request, "Rezervacija atšaukta.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("student_shop")


@require_role([User.Role.STUDENT])
def student_confirm_group_purchase(request: HttpRequest, bonus_id: int) -> HttpResponse:
    bonus = get_object_or_404(BonusItem, pk=bonus_id)
    if request.method == "POST":
        try:
            confirm_group_purchase(request.user, bonus)
            messages.success(request, "Pirkimas patvirtintas.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("student_shop")

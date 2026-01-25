from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Max, Value, Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import (
    Semester,
    SchoolSettings,
    StudentProfile,
    TeacherProfile,
    TeacherBudget,
    BonusItem,
    PointTransaction,
    User,
)


@dataclass
class DomainError(Exception):
    message: str


def get_school_name() -> str:
    settings_row = SchoolSettings.objects.first()
    return settings_row.name if settings_row else "Mokyklos pavadinimas"


def get_active_semester() -> Semester:
    semesters = Semester.objects.filter(is_active=True)
    if not semesters.exists():
        raise DomainError("Nėra aktyvaus semestro.")
    if semesters.count() > 1:
        raise DomainError("Yra keli aktyvūs semestrai. Patikrinkite nustatymus.")
    return semesters.first()


def student_balance_points(student: StudentProfile, semester: Semester) -> int:
    total = (
        PointTransaction.objects.filter(semester=semester, student_profile=student)
        .aggregate(total=Coalesce(Sum("points_delta"), 0))
        .get("total")
    )
    return int(total or 0)


def bonus_used_count(student: StudentProfile, semester: Semester, bonus: BonusItem) -> int:
    return PointTransaction.objects.filter(
        semester=semester,
        student_profile=student,
        tx_type=PointTransaction.TxType.REDEEM,
        bonus_item=bonus,
    ).count()


def award_points(teacher_user: User, student: StudentProfile, points: int, message: str) -> PointTransaction:
    if teacher_user.role != User.Role.TEACHER:
        raise DomainError("Neturite teisės skirti taškų.")
    if points <= 0:
        raise DomainError("Taškai turi būti teigiami.")

    semester = get_active_semester()

    with transaction.atomic():
        try:
            teacher_profile = TeacherProfile.objects.select_for_update().get(user=teacher_user)
        except TeacherProfile.DoesNotExist as exc:
            raise DomainError("Mokytojo profilis nerastas.") from exc
        try:
            budget = TeacherBudget.objects.select_for_update().get(teacher_profile=teacher_profile, semester=semester)
        except TeacherBudget.DoesNotExist as exc:
            raise DomainError("Mokytojo biudžetas šiam semestrui nerastas.") from exc
        if budget.remaining_points < points:
            raise DomainError("Nepakanka biudžeto šiems taškams.")

        budget.spent_points += points
        budget.save(update_fields=["spent_points"])

        tx = PointTransaction.objects.create(
            semester=semester,
            student_profile=student,
            created_by=teacher_user,
            tx_type=PointTransaction.TxType.AWARD,
            points_delta=points,
            message=message,
        )
        return tx


def redeem_bonus(student_user: User, bonus: BonusItem) -> PointTransaction:
    if student_user.role != User.Role.STUDENT:
        raise DomainError("Neturite teisės išpirkti bonusų.")
    if not bonus.is_active:
        raise DomainError("Bonusas neaktyvus.")

    semester = get_active_semester()

    with transaction.atomic():
        try:
            student_profile = StudentProfile.objects.select_for_update().get(user=student_user)
        except StudentProfile.DoesNotExist as exc:
            raise DomainError("Mokinio profilis nerastas.") from exc
        balance = student_balance_points(student_profile, semester)
        if balance < bonus.price_points:
            raise DomainError("Nepakanka taškų šiam bonusui.")

        used = bonus_used_count(student_profile, semester, bonus)
        if used >= bonus.max_uses_per_student:
            raise DomainError("Pasiektas bonuso panaudojimų limitas.")

        tx = PointTransaction.objects.create(
            semester=semester,
            student_profile=student_profile,
            created_by=student_user,
            tx_type=PointTransaction.TxType.REDEEM,
            points_delta=-bonus.price_points,
            message=f"Bonusas: {bonus.title_lt}",
            bonus_item=bonus,
        )
        return tx


def admin_adjust_points(admin_user: User, student: StudentProfile, points: int, message: str) -> PointTransaction:
    if admin_user.role != User.Role.ADMIN:
        raise DomainError("Neturite teisės koreguoti taškų.")
    if points <= 0:
        raise DomainError("Taškai turi būti teigiami.")

    semester = get_active_semester()

    tx = PointTransaction.objects.create(
        semester=semester,
        student_profile=student,
        created_by=admin_user,
        tx_type=PointTransaction.TxType.ADMIN_ADJUST,
        points_delta=points,
        message=message,
    )
    return tx


def top_students(semester: Semester, limit: int = 5) -> Iterable[StudentProfile]:
    future_date = getattr(settings, "SCHOOL_FUTURE_DATE", timezone.now())
    return (
        StudentProfile.objects.annotate(
            total_points=Coalesce(
                Sum("point_transactions__points_delta", filter=Q(point_transactions__semester=semester)),
                0,
            ),
            last_tx_time=Coalesce(
                Max("point_transactions__created_at", filter=Q(point_transactions__semester=semester)),
                Value(future_date),
            ),
        )
        .order_by("-total_points", "last_tx_time", "display_name")[:limit]
    )

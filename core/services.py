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
    GroupPurchase,
    GroupContribution,
    PointTransaction,
    User,
)


@dataclass
class DomainError(Exception):
    message: str


def get_school_settings() -> SchoolSettings | None:
    return SchoolSettings.objects.first()


def get_school_name() -> str:
    settings_row = get_school_settings()
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


def student_reserved_points(student: StudentProfile, semester: Semester) -> int:
    total = (
        GroupContribution.objects.filter(
            student_profile=student,
            group_purchase__semester=semester,
            group_purchase__status__in=[
                GroupPurchase.Status.OPEN,
                GroupPurchase.Status.AWAITING_CONFIRMATION,
            ],
        )
        .aggregate(total=Coalesce(Sum("amount"), 0))
        .get("total")
    )
    return int(total or 0)


def get_or_create_group_purchase(semester: Semester, bonus: BonusItem) -> GroupPurchase:
    group_purchase = GroupPurchase.objects.filter(
        semester=semester,
        bonus_item=bonus,
        status__in=[GroupPurchase.Status.OPEN, GroupPurchase.Status.AWAITING_CONFIRMATION],
    ).first()
    if group_purchase:
        return group_purchase
    return GroupPurchase.objects.create(semester=semester, bonus_item=bonus)


def reserve_group_points(student_user: User, bonus: BonusItem, amount: int) -> GroupContribution:
    if student_user.role != User.Role.STUDENT:
        raise DomainError("Neturite teisės rezervuoti taškų.")
    if amount <= 0:
        raise DomainError("Rezervuojamų taškų kiekis turi būti teigiamas.")
    if not bonus.is_active:
        raise DomainError("Bonusas neaktyvus.")

    semester = get_active_semester()

    try:
        student_profile = StudentProfile.objects.get(user=student_user)
    except StudentProfile.DoesNotExist as exc:
        raise DomainError("Mokinio profilis nerastas.") from exc

    if bonus_used_count(student_profile, semester, bonus) >= bonus.max_uses_per_student:
        raise DomainError("Pasiektas bonuso panaudojimų limitas.")

    with transaction.atomic():
        group_purchase = get_or_create_group_purchase(semester, bonus)
        group_purchase = GroupPurchase.objects.select_for_update().get(pk=group_purchase.pk)

        if group_purchase.status != GroupPurchase.Status.OPEN:
            raise DomainError("Grupinis pirkimas jau laukia patvirtinimų.")

        contribution = (
            GroupContribution.objects.select_for_update()
            .filter(group_purchase=group_purchase, student_profile=student_profile)
            .first()
        )
        existing_amount = contribution.amount if contribution else 0

        total_other = (
            GroupContribution.objects.filter(group_purchase=group_purchase)
            .exclude(student_profile=student_profile)
            .aggregate(total=Coalesce(Sum("amount"), 0))
            .get("total")
        )
        remaining_needed = max(bonus.price_points - int(total_other or 0), 0)
        max_allowed = remaining_needed + existing_amount
        if amount > max_allowed:
            raise DomainError("Rezervuojamų taškų per daug šiam bonusui.")

        balance = student_balance_points(student_profile, semester)
        reserved_total = student_reserved_points(student_profile, semester)
        available = balance - reserved_total + existing_amount
        if amount > available:
            raise DomainError("Nepakanka laisvų taškų rezervacijai.")

        if contribution:
            contribution.amount = amount
            contribution.confirmed_at = None
            contribution.save(update_fields=["amount", "confirmed_at", "updated_at"])
        else:
            contribution = GroupContribution.objects.create(
                group_purchase=group_purchase,
                student_profile=student_profile,
                amount=amount,
            )

        total_reserved = (
            GroupContribution.objects.filter(group_purchase=group_purchase)
            .aggregate(total=Coalesce(Sum("amount"), 0))
            .get("total")
        )
        if int(total_reserved or 0) >= bonus.price_points:
            group_purchase.status = GroupPurchase.Status.AWAITING_CONFIRMATION
            group_purchase.save(update_fields=["status"])
        return contribution


def withdraw_group_reservation(student_user: User, bonus: BonusItem) -> None:
    if student_user.role != User.Role.STUDENT:
        raise DomainError("Neturite teisės atšaukti rezervacijos.")

    semester = get_active_semester()
    try:
        student_profile = StudentProfile.objects.get(user=student_user)
    except StudentProfile.DoesNotExist as exc:
        raise DomainError("Mokinio profilis nerastas.") from exc

    group_purchase = GroupPurchase.objects.filter(
        semester=semester,
        bonus_item=bonus,
        status__in=[GroupPurchase.Status.OPEN, GroupPurchase.Status.AWAITING_CONFIRMATION],
    ).first()
    if not group_purchase:
        raise DomainError("Rezervacijos nerastos.")

    with transaction.atomic():
        group_purchase = GroupPurchase.objects.select_for_update().get(pk=group_purchase.pk)
        if group_purchase.status == GroupPurchase.Status.COMPLETED:
            raise DomainError("Rezervacija jau užbaigta.")

        contributors = GroupContribution.objects.filter(group_purchase=group_purchase)
        if contributors.exclude(student_profile=student_profile).exists():
            raise DomainError("Rezervacijos atšaukti negalima, nes prisidėjo kiti mokiniai.")

        contribution = contributors.filter(student_profile=student_profile).first()
        if not contribution:
            raise DomainError("Rezervacijos nerastos.")
        contribution.delete()
        group_purchase.delete()


def confirm_group_purchase(student_user: User, bonus: BonusItem) -> None:
    if student_user.role != User.Role.STUDENT:
        raise DomainError("Neturite teisės patvirtinti pirkimo.")

    semester = get_active_semester()
    try:
        student_profile = StudentProfile.objects.get(user=student_user)
    except StudentProfile.DoesNotExist as exc:
        raise DomainError("Mokinio profilis nerastas.") from exc

    group_purchase = GroupPurchase.objects.filter(
        semester=semester,
        bonus_item=bonus,
        status=GroupPurchase.Status.AWAITING_CONFIRMATION,
    ).first()
    if not group_purchase:
        raise DomainError("Nėra grupinio pirkimo patvirtinimui.")

    with transaction.atomic():
        group_purchase = GroupPurchase.objects.select_for_update().get(pk=group_purchase.pk)
        contribution = (
            GroupContribution.objects.select_for_update()
            .filter(group_purchase=group_purchase, student_profile=student_profile)
            .first()
        )
        if not contribution:
            raise DomainError("Jūs neprisidėjote prie šio pirkimo.")
        if contribution.confirmed_at:
            return

        balance = student_balance_points(student_profile, semester)
        reserved_total = student_reserved_points(student_profile, semester)
        available = balance - reserved_total + contribution.amount
        if contribution.amount > available:
            raise DomainError("Nepakanka taškų patvirtinti pirkimą.")

        contribution.confirmed_at = timezone.now()
        contribution.save(update_fields=["confirmed_at", "updated_at"])

        all_confirmed = not GroupContribution.objects.filter(
            group_purchase=group_purchase, confirmed_at__isnull=True
        ).exists()
        if not all_confirmed:
            return

        for entry in group_purchase.contributions.select_for_update():
            PointTransaction.objects.create(
                semester=semester,
                student_profile=entry.student_profile,
                created_by=entry.student_profile.user,
                tx_type=PointTransaction.TxType.REDEEM,
                points_delta=-entry.amount,
                message=f"Grupinis pirkimas: {bonus.title_lt}",
                bonus_item=bonus,
            )
        group_purchase.status = GroupPurchase.Status.COMPLETED
        group_purchase.save(update_fields=["status"])


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
            lifetime_points=Coalesce(
                Sum("point_transactions__points_delta", filter=Q(point_transactions__points_delta__gt=0)),
                0,
            ),
            last_tx_time=Coalesce(
                Max("point_transactions__created_at", filter=Q(point_transactions__semester=semester)),
                Value(future_date),
            ),
        )
        .order_by("-total_points", "last_tx_time", "display_name")[:limit]
    )
